# bot/solana/phantom.py
"""
Phantom Wallet deeplink генератор.

Позволяет открыть Phantom с готовой транзакцией
одним нажатием — без кастодиального хранения ключей.
"""

import urllib.parse


def build_phantom_deeplink(
    transaction_b64: str,
    redirect_url: str = "https://ratzon.vercel.app",
) -> str:
    """
    Строит deeplink для Phantom который открывает
    готовую транзакцию на подпись.

    Args:
        transaction_b64: base64 транзакция от Jupiter
        redirect_url: куда вернуть пользователя после подписи

    Returns:
        https://phantom.app/... universal link
    """
    params = _build_phantom_params(transaction_b64, redirect_url)

    # Universal link. Good for Telegram URL buttons and most mobile browsers,
    # but on desktop it opens Phantom's website, not the browser extension.
    return f"https://phantom.app/ul/v1/signAndSendTransaction?{params}"


def build_phantom_app_deeplink(
    transaction_b64: str,
    redirect_url: str = "https://ratzon.vercel.app",
) -> str:
    """
    Строит custom-scheme deeplink для прямого открытия Phantom mobile app.

    Используется фронтендом на mobile как same-tab navigation. Для Telegram
    inline-кнопок оставляем https universal link.
    """
    params = _build_phantom_params(transaction_b64, redirect_url)
    return f"phantom://v1/signAndSendTransaction?{params}"


def build_phantom_browse_deeplink(
    url: str = "https://ratzon.vercel.app",
    ref: str = "https://ratzon.vercel.app",
) -> str:
    """Строит ссылку для открытия сайта внутри Phantom mobile browser."""
    encoded_url = urllib.parse.quote(url, safe="")
    encoded_ref = urllib.parse.quote(ref, safe="")
    return f"https://phantom.app/ul/browse/{encoded_url}?ref={encoded_ref}"


def _build_phantom_params(transaction_b64: str, redirect_url: str) -> str:
    return urllib.parse.urlencode({
        "transaction": transaction_b64,
        "redirect_link": redirect_url,
    })


def build_solflare_deeplink(transaction_b64: str) -> str:
    """Альтернатива — Solflare кошелёк."""
    params = urllib.parse.urlencode({
        "transaction": transaction_b64,
        "network": "mainnet-beta",
    })
    return f"https://solflare.com/ul/v1/signAndSendTransaction?{params}"
