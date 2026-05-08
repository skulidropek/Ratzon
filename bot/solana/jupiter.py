# bot/solana/jupiter.py
"""
Jupiter V6 Quote API интеграция.
Документация: https://station.jup.ag/docs/apis/swap-api

Реальные данные, без мока — это ключевое для демо!
"""

import logging
from typing import Optional

import aiohttp

from .tokens import get_mint, to_lamports, from_lamports, get_decimals
from bot.intents.models import QuoteResult, SwapIntent

logger = logging.getLogger(__name__)

JUPITER_QUOTE_URL = "https://api.jup.ag/swap/v1/quote"
JUPITER_SWAP_URL = "https://api.jup.ag/swap/v1/swap"


class JupiterClient:
    """
    Клиент для Jupiter Aggregator API.

    Только quote (не swap) для MVP — реальные данные без подписи.
    """

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_quote(self, intent: SwapIntent) -> tuple[QuoteResult | None, dict | None]:
        """
        Получает лучшую котировку для swap от Jupiter.

        Returns:
            QuoteResult с данными маршрута, или None если маршрут не найден.
        """
        input_mint = get_mint(intent.input_token)
        output_mint = get_mint(intent.output_token)

        if not input_mint:
            logger.warning(f"Unknown input token mint: {intent.input_token}")
            return None, None
        if not output_mint:
            logger.warning(f"Unknown output token mint: {intent.output_token}")
            return None, None

        amount_raw = to_lamports(intent.amount, intent.input_token)

        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount_raw),
            "slippageBps": str(intent.slippage_bps),
            "onlyDirectRoutes": "false",
            "asLegacyTransaction": "false",
        }

        logger.info(
            f"Requesting Jupiter quote: {intent.amount} {intent.input_token} → {intent.output_token}"
        )

        try:
            session = await self._get_session()
            async with session.get(JUPITER_QUOTE_URL, params=params) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error(f"Jupiter API error {resp.status}: {body}")
                    return None, None

                data = await resp.json()
                return self._parse_quote(data, intent), data

        except aiohttp.ClientError as e:
            logger.error(f"Jupiter API connection error: {e}")
            return None, None
        except Exception as e:
            logger.error(f"Unexpected error in Jupiter quote: {e}", exc_info=True)
            return None, None

    async def get_swap_transaction(
        self,
        quote_response: dict,
        user_wallet: str,
    ) -> str | None:
        """
        Получает готовую (неподписанную) транзакцию от Jupiter.

        Returns:
            base64-encoded transaction string
        """
        payload = {
            "quoteResponse": quote_response,
            "userPublicKey": user_wallet,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": "auto",
        }

        try:
            session = await self._get_session()
            async with session.post(
                JUPITER_SWAP_URL,
                json=payload,
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error(f"Jupiter swap tx error {resp.status}: {body}")
                    return None

                data = await resp.json()
                # Jupiter возвращает base64 транзакцию
                return data.get("swapTransaction")

        except Exception as e:
            logger.error(f"Error getting swap transaction: {e}")
            return None

    def _parse_quote(self, data: dict, intent: SwapIntent) -> QuoteResult:
        """Преобразует сырой ответ Jupiter → QuoteResult"""

        # Jupiter возвращает outAmount в наименьших единицах
        out_amount_raw = int(data.get("outAmount", 0))
        out_decimals = get_decimals(intent.output_token)
        out_amount = out_amount_raw / (10**out_decimals)

        # Цена воздействия (priceImpactPct — строка типа "0.001")
        price_impact_raw = data.get("priceImpactPct", "0")
        try:
            price_impact = float(price_impact_raw) * 100  # в проценты
        except (ValueError, TypeError):
            price_impact = 0.0

        # Строим читаемый маршрут
        route_label = self._build_route_label(data, intent)

        # Комиссия платформы
        fees_sol = self._extract_fees(data)

        return QuoteResult(
            input_token=intent.input_token,
            output_token=intent.output_token,
            input_amount=intent.amount,
            output_amount=out_amount,
            price_impact_pct=price_impact,
            route_label=route_label,
            fees_sol=fees_sol,
        )

    def _build_route_label(self, data: dict, intent: SwapIntent) -> str:
        """
        Строит читаемый маршрут из routePlan Jupiter.
        Пример: "SOL → Raydium → USDC"
        """
        route_plan = data.get("routePlan", [])

        if not route_plan:
            return f"{intent.input_token} → {intent.output_token}"

        parts = [intent.input_token]
        seen_mints = set()

        for leg in route_plan:
            swap_info = leg.get("swapInfo", {})
            amm_label = swap_info.get("label", "DEX")
            out_mint = swap_info.get("outputMint", "")

            # Не дублируем
            if out_mint not in seen_mints:
                seen_mints.add(out_mint)
                # Находим символ по mint (упрощённо)
                out_symbol = self._mint_to_symbol(out_mint, intent.output_token)
                parts.append(f"[{amm_label}]")
                parts.append(out_symbol)

        return " → ".join(parts)

    def _mint_to_symbol(self, mint: str, fallback: str) -> str:
        """Обратное преобразование mint → symbol для красивого отображения маршрута."""
        from .tokens import TOKEN_MINTS

        for symbol, m in TOKEN_MINTS.items():
            if m == mint:
                return symbol
        return fallback

    def _extract_fees(self, data: dict) -> float:
        """Извлекает суммарные комиссии из ответа Jupiter."""
        try:
            fees = data.get("fees", {})
            platform_fee = fees.get("platformFeeBps", 0)
            # Упрощённо: возвращаем bps как число
            return platform_fee / 10000  # в % от суммы
        except Exception:
            return 0.0


# Глобальный синглтон
jupiter_client = JupiterClient()
