import io
import json
import logging

import requests
from fdk import response

PROFILE_USERNAME = "solamentedeya.m"
WEB_PROFILE_INFO_URL = "https://www.instagram.com/api/v1/users/web_profile_info/"
# App id público que el propio front de Instagram manda en esta llamada;
# no es un secreto, es fijo para cualquier cliente web logueado o no.
IG_APP_ID = "936619743392459"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_followers() -> int | None:
    """Pega directo al endpoint JSON interno que el propio front de
    Instagram llama al cargar un perfil público (`web_profile_info`), sin
    necesidad de un browser: alcanza con mandar el header `x-ig-app-id`
    que ese request usa. Se probó primero con Playwright (mismo enfoque que
    Spotify), pero Chromium se caía consistentemente dentro de OCI
    Functions -- Instagram es bastante más agresivo detectando/bloqueando
    Chromium headless desde IPs de datacenter que Spotify. Pegarle directo
    a la API evita ese problema por completo."""
    resp = requests.get(
        WEB_PROFILE_INFO_URL,
        params={"username": PROFILE_USERNAME},
        headers={
            "x-ig-app-id": IG_APP_ID,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept": "*/*",
        },
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    return body["data"]["user"]["edge_followed_by"]["count"]


def handler(ctx, data: io.BytesIO = None):
    try:
        followers = get_followers()
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
