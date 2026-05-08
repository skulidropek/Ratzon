# bot/config.py
"""
Конфигурация проекта — всё берётся из переменных окружения.
"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    # Обязательно
    bot_token: str

    # Опционально
    log_level: str = "INFO"
    jupiter_rpc_url: str = "https://quote-api.jup.ag/v6"
    
    # RPC для будущего использования (исполнение транзакций)
    solana_rpc_url: str = "https://api.mainnet-beta.solana.com"

    # Для демо-режима (мок кошелёк)
    demo_wallet: str = "Demo1111111111111111111111111111111111111111"

    # Локальный web frontend рядом с ботом
    start_frontend_with_bot: bool = True
    frontend_host: str = "0.0.0.0"
    frontend_port: int = 4000
    frontend_dir: str = "frontend"
    frontend_command: str = ""
    frontend_mode: str = "auto"
    web_app_url: str = ""
    api_port: int = 8080

    @classmethod
    def from_env(cls) -> "Config":
        token = os.getenv("BOT_TOKEN")
        if not token:
            raise ValueError("BOT_TOKEN environment variable is required")

        start_frontend_with_bot = _env_bool("START_FRONTEND_WITH_BOT", True)
        api_port = int(os.getenv("BOT_API_PORT", os.getenv("API_PORT", "8080")))
        frontend_port = int(os.getenv("FRONTEND_PORT") or os.getenv("PORT") or "4000")
        if start_frontend_with_bot and frontend_port == api_port:
            api_port = 8081 if frontend_port == 8080 else 8080

        return cls(
            bot_token=token,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            solana_rpc_url=os.getenv(
                "SOLANA_RPC_URL",
                "https://api.mainnet-beta.solana.com"
            ),
            demo_wallet=os.getenv(
                "DEMO_WALLET",
                "Demo1111111111111111111111111111111111111111"
            ),
            start_frontend_with_bot=start_frontend_with_bot,
            frontend_host=os.getenv("FRONTEND_HOST", "0.0.0.0"),
            frontend_port=frontend_port,
            frontend_dir=os.getenv("FRONTEND_DIR", "frontend"),
            frontend_command=os.getenv("FRONTEND_COMMAND", ""),
            frontend_mode=os.getenv("FRONTEND_MODE", "auto").strip().lower(),
            web_app_url=_env_url(
                "WEB_APP_URL",
                "TELEGRAM_WEB_APP_URL",
                "FRONTEND_PUBLIC_URL",
                "FRONTEND_URL",
                "RAILWAY_PUBLIC_DOMAIN",
            ),
            api_port=api_port,
        )


# Глобальный конфиг (инициализируется при старте)
config: Config | None = None


def get_config() -> Config:
    global config
    if config is None:
        config = Config.from_env()
    return config


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_url(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return _normalize_url(value)
    return ""


def _normalize_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"
