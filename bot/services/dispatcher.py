# bot/services/dispatcher.py
import logging
from dataclasses import dataclass

from bot.intents.models import (
    AnyIntent, IntentType, SwapIntent, BalanceIntent,
    PriceIntent, RateIntent, CompareIntent,
    QuoteResult, RiskReport,
)
from bot.solana.jupiter import jupiter_client
from bot.solana.jupiter_price import jupiter_price_client
from bot.risk.engine import risk_engine
from bot.services import formatter

logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    text: str
    show_confirm_button: bool = False
    intent: AnyIntent = None
    quote: QuoteResult = None
    risk: RiskReport = None
    quote_raw: dict = None


class IntentDispatcher:

    async def dispatch(self, intent: AnyIntent) -> DispatchResult:
        logger.info(f"Dispatching: type={intent.intent_type}")

        if intent.intent_type == IntentType.SWAP:
            return await self._handle_swap(intent)
        elif intent.intent_type == IntentType.PRICE:
            return await self._handle_price(intent)
        elif intent.intent_type == IntentType.RATE:
            return await self._handle_rate(intent)
        elif intent.intent_type == IntentType.COMPARE:
            return await self._handle_compare(intent)
        elif intent.intent_type == IntentType.BALANCE:
            return self._handle_balance(intent)
        else:
            return DispatchResult(
                text=formatter.format_intent_unknown(intent.raw_text),
                intent=intent,
            )

    async def _handle_swap(self, intent: SwapIntent) -> DispatchResult:
        if not intent.is_valid():
            return DispatchResult(
                text=formatter.format_parse_error(intent), intent=intent,
            )
        intent.slippage_bps = self._resolve_slippage(intent)
        quote, raw = await jupiter_client.get_quote(intent)
        if quote is None:
            return DispatchResult(
                text=formatter.format_no_route(intent), intent=intent,
            )
        risk = risk_engine.evaluate(intent, quote)
        return DispatchResult(
            text=formatter.format_swap_response(intent, quote, risk),
            show_confirm_button=True,
            intent=intent, quote=quote, risk=risk, quote_raw=raw,
        )

    def _resolve_slippage(self, intent: SwapIntent) -> int:
        if intent.input_token == "USDC" or intent.output_token == "USDC":
            return 30

        low_liquidity = {"BONK", "WIF", "MYRO", "BOME", "POPCAT", "SLERF"}
        if intent.input_token in low_liquidity or intent.output_token in low_liquidity:
            return 300

        return intent.slippage_bps or 50

    async def _handle_price(self, intent: PriceIntent) -> DispatchResult:
        if not intent.token:
            return DispatchResult(
                text="❓ Which token? Example: <code>Price of SOL</code>",
                intent=intent,
            )
        price_data = await jupiter_price_client.get_price(intent.token)
        if price_data:
            text = formatter.format_price_real(intent.token, price_data)
        else:
            text = formatter.format_price_unavailable(intent.token)
        return DispatchResult(text=text, intent=intent)

    async def _handle_rate(self, intent: RateIntent) -> DispatchResult:
        if not intent.input_token or not intent.output_token:
            return DispatchResult(
                text="❓ Example: <code>Rate SOL to USDC</code>", intent=intent,
            )
        swap_intent = SwapIntent(
            raw_text=intent.raw_text, intent_type=IntentType.SWAP,
            confidence=1.0, amount=intent.amount or 1.0,
            input_token=intent.input_token, output_token=intent.output_token,
        )
        quote, _ = await jupiter_client.get_quote(swap_intent)
        if quote is None:
            return DispatchResult(
                text=formatter.format_no_route(swap_intent), intent=intent,
            )
        return DispatchResult(
            text=formatter.format_rate(intent, quote),
            intent=intent, quote=quote,
        )

    async def _handle_compare(self, intent: CompareIntent) -> DispatchResult:
        logger.info("ENTER _handle_compare")

        if not intent.token_a or not intent.token_b:
            return DispatchResult(
                text="❓ Example: <code>Compare SOL and BONK</code>", intent=intent,
            )

        logger.info("CALLING get_prices")
        prices = await jupiter_price_client.get_prices([intent.token_a, intent.token_b])

        logger.info(f"PRICES RESULT: {prices}")

        text = formatter.format_compare(
            intent.token_a, prices.get(intent.token_a),
            intent.token_b, prices.get(intent.token_b),
        )
        return DispatchResult(text=text, intent=intent)

    def _handle_balance(self, intent: BalanceIntent) -> DispatchResult:
        return DispatchResult(
            text=formatter.format_balance_mock(), intent=intent,
        )


intent_dispatcher = IntentDispatcher()
