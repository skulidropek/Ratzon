# bot/api_server.py
"""
HTTP API сервер для фронтенда.
Фронтенд → POST /intent → Python бот → Jupiter → JSON response

Запуск вместе с ботом:
  python -m bot.api_server
"""

import asyncio
import json
import logging
import re
from aiohttp import web

from bot.intents.models import IntentType
from bot.intents.parser import intent_parser
from bot.services.dispatcher import intent_dispatcher
from bot.solana.jupiter import jupiter_client
from bot.solana.phantom import (
    build_phantom_app_deeplink,
    build_phantom_browse_deeplink,
    build_phantom_deeplink,
)

logger = logging.getLogger(__name__)


async def handle_intent(request: web.Request) -> web.Response:
    """POST /intent — парсит и обрабатывает интент."""
    try:
        body = await request.json()
        message = body.get("message", "").strip()

        if not message:
            return web.json_response(
                {"error": "message is required"}, status=400
            )

        # Парсим интент
        intent = await intent_parser.parse(message)

        # Диспетчеризируем
        result = await intent_dispatcher.dispatch(intent)

        # Сериализуем ответ
        response_data = {
            "text": result.text,
            "intent": {
                "type": intent.intent_type.value,
                "confidence": intent.confidence,
                "amount": getattr(intent, "amount", None),
                "input_token": getattr(intent, "input_token", None),
                "output_token": getattr(intent, "output_token", None),
            },
            "quote": None,
            "risk": None,
        }

        if result.quote:
            response_data["quote"] = {
                "input_token": result.quote.input_token,
                "output_token": result.quote.output_token,
                "input_amount": result.quote.input_amount,
                "output_amount": result.quote.output_amount,
                "price_impact_pct": result.quote.price_impact_pct,
                "route_label": result.quote.route_label,
                "fees_sol": result.quote.fees_sol,
                "route_score": _compute_route_quality(result.risk, result.quote),
            }

        if result.risk:
            response_data["risk"] = {
                "level": result.risk.level.value,
                "score": result.risk.score,
                "warnings": result.risk.warnings,
            }

        return web.json_response(response_data)

    except json.JSONDecodeError:
        return web.json_response({"error": "invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"API error: {e}", exc_info=True)
        return web.json_response({"error": "internal error"}, status=500)


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({
        "status": "ok",
        "service": "ratzon-bot-api",
    })


async def handle_swap(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        message = body.get("message", "").strip()
        wallet = body.get("wallet", "").strip()

        if not message:
            return web.json_response(
                {"error": "message is required"}, status=400
            )

        if not wallet or not _is_valid_wallet(wallet):
            return web.json_response(
                {"error": "valid Solana wallet address is required"}, status=400
            )

        intent = await intent_parser.parse(message)
        if intent.intent_type != IntentType.SWAP:
            return web.json_response(
                {"error": "Only swap intents can be confirmed"}, status=400
            )

        quote, quote_raw = await jupiter_client.get_quote(intent)
        if quote is None or quote_raw is None:
            return web.json_response(
                {"error": "Failed to find a valid quote"}, status=502
            )

        tx_b64 = await jupiter_client.get_swap_transaction(
            quote_response=quote_raw,
            user_wallet=wallet,
        )

        if not tx_b64:
            return web.json_response(
                {"error": "Failed to prepare transaction"}, status=502
            )

        return web.json_response({
            "transaction": tx_b64,
            "phantom_url": build_phantom_deeplink(tx_b64),
            "phantom_app_url": build_phantom_app_deeplink(tx_b64),
            "phantom_browse_url": build_phantom_browse_deeplink(),
        })

    except json.JSONDecodeError:
        return web.json_response({"error": "invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Swap API error: {e}", exc_info=True)
        return web.json_response({"error": "internal error"}, status=500)


def _is_valid_wallet(address: str) -> bool:
    return bool(re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", address))


def _compute_route_quality(risk, quote) -> int | None:
    if not risk or not quote:
        return None

    quality = 100
    quality -= min(risk.score, 80)
    quality -= min(quote.price_impact_pct, 20) * 2
    quality -= min(quote.fees_sol * 1000, 15)
    return max(0, round(quality))


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/intent", handle_intent)
    app.router.add_post("/swap", handle_swap)
    app.router.add_get("/health", handle_health)

    # CORS для фронтенда
    @web.middleware
    async def cors_middleware(request, handler):
        if request.method == "OPTIONS":
            response = web.Response()
        else:
            response = await handler(request)

        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    app.middlewares.append(cors_middleware)
    return app


async def start_api_server(port: int = 8080):
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Bot API server running on http://0.0.0.0:{port}")
    return runner
