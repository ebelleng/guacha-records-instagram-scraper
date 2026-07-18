import asyncio
import io
import json
import logging

from fdk import response
from playwright.async_api import async_playwright

PROFILE_URL = "https://www.instagram.com/solamentedeya.m/"
PROFILE_USERNAME = "solamentedeya.m"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_followers() -> int | None:
    """Abre la página pública del perfil e intercepta la respuesta de
    `web_profile_info` (api/v1/users/web_profile_info/?username=...), la
    llamada interna que Instagram dispara al cargar el perfil y trae
    data.user.edge_followed_by.count. Igual que en Spotify, ese número no
    vive en el HTML servido de entrada sino que llega vía una llamada de
    red propia del front, así que hace falta un browser real para
    disparerla y poder leer la respuesta."""
    followers = None

    async def on_response(resp):
        nonlocal followers
        if followers is not None or "web_profile_info" not in resp.url:
            return
        if PROFILE_USERNAME not in resp.url:
            return
        try:
            body = await resp.json()
            followers = body["data"]["user"]["edge_followed_by"]["count"]
        except (KeyError, TypeError, ValueError):
            pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        try:
            page = await browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                )
            )
            page.on("response", lambda resp: asyncio.ensure_future(on_response(resp)))
            await page.goto(PROFILE_URL, wait_until="networkidle", timeout=25000)
            if followers is None:
                await page.wait_for_timeout(3000)
        finally:
            await browser.close()

    return followers


async def handler(ctx, data: io.BytesIO = None):
    try:
        followers = await get_followers()
        body = {
            "profile_username": PROFILE_USERNAME,
            "followers": followers,
            "ok": followers is not None,
        }
        status = 200 if followers is not None else 502
    except Exception as e:
        logger.exception("Error scraping Instagram followers")
        body = {
            "profile_username": PROFILE_USERNAME,
            "followers": None,
            "ok": False,
            "error": str(e),
        }
        status = 500

    return response.Response(
        ctx,
        response_data=json.dumps(body),
        headers={"Content-Type": "application/json"},
        status_code=status,
    )
