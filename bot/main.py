# bot/main.py
"""
Точка входа — запускает Telegram бот + HTTP API + web frontend.
"""

import asyncio
import logging
import os
import shlex
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import MenuButtonWebApp, WebAppInfo

from bot.config import get_config
from bot.handlers import start, intent_handler
from bot.solana.jupiter import jupiter_client
from bot.solana.jupiter_price import jupiter_price_client
from bot.intents.llm_parser import llm_parser
from bot.api_server import start_api_server


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


async def start_frontend_process(cfg, logger: logging.Logger):
    if not cfg.start_frontend_with_bot:
        logger.info("Frontend autostart disabled.")
        return None

    frontend_dir = Path(cfg.frontend_dir)
    if not frontend_dir.is_absolute():
        frontend_dir = Path(__file__).resolve().parents[1] / frontend_dir

    package_json = frontend_dir / "package.json"
    if not package_json.exists():
        logger.warning("Frontend autostart skipped: %s not found", package_json)
        return None

    if await _is_port_open("127.0.0.1", cfg.frontend_port):
        logger.info("Frontend already running on port %s; skipping autostart.", cfg.frontend_port)
        return None

    command = _resolve_frontend_command(cfg, frontend_dir)
    if not command:
        logger.warning("Frontend autostart skipped: no node package runner found.")
        return None

    env = os.environ.copy()
    if "BOT_API_URL" not in env or _is_loopback_url(env["BOT_API_URL"]):
        env["BOT_API_URL"] = f"http://localhost:{cfg.api_port}"

    logger.info("Starting frontend: %s", " ".join(command))
    try:
        return await asyncio.create_subprocess_exec(
            *command,
            cwd=str(frontend_dir),
            env=env,
        )
    except FileNotFoundError as exc:
        logger.warning("Frontend autostart failed: %s", exc)
        return None


def _resolve_frontend_command(cfg, frontend_dir: Path) -> list[str] | None:
    if cfg.frontend_command:
        return shlex.split(os.path.expandvars(cfg.frontend_command))

    frontend_mode = _resolve_frontend_mode(cfg, frontend_dir)

    next_bin = frontend_dir / "node_modules" / ".bin" / "next"
    if next_bin.exists():
        return [
            str(next_bin),
            frontend_mode,
            "--hostname",
            cfg.frontend_host,
            "--port",
            str(cfg.frontend_port),
        ]

    if shutil.which("corepack"):
        return [
            "corepack",
            "pnpm",
            frontend_mode,
            "--",
            "--hostname",
            cfg.frontend_host,
            "--port",
            str(cfg.frontend_port),
        ]

    if shutil.which("npm"):
        return [
            "npm",
            "run",
            frontend_mode,
            "--",
            "--hostname",
            cfg.frontend_host,
            "--port",
            str(cfg.frontend_port),
        ]

    return None


def _resolve_frontend_mode(cfg, frontend_dir: Path) -> str:
    if cfg.frontend_mode in {"dev", "start"}:
        return cfg.frontend_mode

    has_production_build = (frontend_dir / ".next" / "BUILD_ID").exists()
    is_production_runtime = (
        os.getenv("NODE_ENV") == "production"
        or bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))
    )
    if has_production_build and is_production_runtime:
        return "start"
    return "dev"


def _is_loopback_url(value: str) -> bool:
    try:
        hostname = urlparse(value).hostname
    except ValueError:
        return False
    return hostname in {"localhost", "127.0.0.1", "0.0.0.0"}


async def _is_port_open(host: str, port: int) -> bool:
    try:
        reader, writer = await asyncio.open_connection(host, port)
    except OSError:
        return False

    writer.close()
    await writer.wait_closed()
    return True


async def stop_frontend_process(process, logger: logging.Logger):
    if process is None or process.returncode is not None:
        return

    logger.info("Stopping frontend...")
    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=10)
    except asyncio.TimeoutError:
        logger.warning("Frontend did not stop gracefully; killing process.")
        process.kill()
        await process.wait()


async def configure_telegram_web_app(bot: Bot, cfg, logger: logging.Logger):
    if not cfg.web_app_url:
        logger.warning(
            "Telegram WebApp URL is not configured. "
            "Set WEB_APP_URL to the public HTTPS frontend URL."
        )
        return

    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Open Ratzon",
                web_app=WebAppInfo(url=cfg.web_app_url),
            )
        )
        logger.info("Telegram WebApp menu button configured: %s", cfg.web_app_url)
    except Exception:
        logger.warning("Failed to configure Telegram WebApp menu button.", exc_info=True)


async def main():
    cfg = get_config()
    setup_logging(cfg.log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting Ratzon...")

    # Telegram бот
    bot = Bot(
        token=cfg.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(intent_handler.router)
    await configure_telegram_web_app(bot, cfg, logger)

    # HTTP API для frontend server routes.
    api_runner = await start_api_server(port=cfg.api_port)
    frontend_process = await start_frontend_process(cfg, logger)

    # Проверяем QVAC
    qvac_ok = await llm_parser.is_available()
    if qvac_ok:
        logger.info("QVAC LLM service: CONNECTED")
    else:
        logger.warning("QVAC LLM service: NOT AVAILABLE (using regex fallback)")

    logger.info("Bot + API server running. Starting polling...")

    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await stop_frontend_process(frontend_process, logger)
        await jupiter_client.close()
        await jupiter_price_client.close()
        await llm_parser.close()
        await api_runner.cleanup()
        await bot.session.close()
        logger.info("Stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
