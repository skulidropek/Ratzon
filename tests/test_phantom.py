from urllib.parse import parse_qs, urlparse

from bot.solana.phantom import (
    build_phantom_app_deeplink,
    build_phantom_browse_deeplink,
    build_phantom_deeplink,
)


def test_build_phantom_universal_link():
    url = build_phantom_deeplink("abc+/=", redirect_url="https://ratzon.vercel.app/cb")
    parsed = urlparse(url)

    assert parsed.scheme == "https"
    assert parsed.netloc == "phantom.app"
    assert parsed.path == "/ul/v1/signAndSendTransaction"

    params = parse_qs(parsed.query)
    assert params["transaction"] == ["abc+/="]
    assert params["redirect_link"] == ["https://ratzon.vercel.app/cb"]


def test_build_phantom_app_deeplink():
    url = build_phantom_app_deeplink("abc+/=", redirect_url="https://ratzon.vercel.app/cb")
    parsed = urlparse(url)

    assert parsed.scheme == "phantom"
    assert parsed.netloc == "v1"
    assert parsed.path == "/signAndSendTransaction"

    params = parse_qs(parsed.query)
    assert params["transaction"] == ["abc+/="]
    assert params["redirect_link"] == ["https://ratzon.vercel.app/cb"]


def test_build_phantom_browse_deeplink():
    url = build_phantom_browse_deeplink(
        "https://ratzon.vercel.app/swap?intent=SOL",
        ref="https://ratzon.vercel.app",
    )
    parsed = urlparse(url)

    assert parsed.scheme == "https"
    assert parsed.netloc == "phantom.app"
    assert parsed.path == "/ul/browse/https%3A%2F%2Fratzon.vercel.app%2Fswap%3Fintent%3DSOL"

    params = parse_qs(parsed.query)
    assert params["ref"] == ["https://ratzon.vercel.app"]


if __name__ == "__main__":
    test_build_phantom_universal_link()
    test_build_phantom_app_deeplink()
    test_build_phantom_browse_deeplink()
    print("OK")
