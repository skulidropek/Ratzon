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
from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

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
    env.setdefault("BOT_API_URL", "http://localhost:8080")

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
        return shlex.split(cfg.frontend_command)

    next_bin = frontend_dir / "node_modules" / ".bin" / "next"
    if next_bin.exists():
        return [
            str(next_bin),
            "dev",
            "--hostname",
            cfg.frontend_host,
            "--port",
            str(cfg.frontend_port),
        ]

    if shutil.which("corepack"):
        return [
            "corepack",
            "pnpm",
            "dev",
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
            "dev",
            "--",
            "--hostname",
            cfg.frontend_host,
            "--port",
            str(cfg.frontend_port),
        ]

    return None


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

    # HTTP API для фронтенда (порт 8080)
    api_runner = await start_api_server(port=8080)
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
