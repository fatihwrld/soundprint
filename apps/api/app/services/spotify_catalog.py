"""Official Spotify Web API access via Client Credentials (app-only).

Client Credentials still works in dev mode for *public catalog* endpoints
(tracks, albums, search) — which is all we need for label/copyright data.
Requires SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET (free developer app).
"""

import logging
import time

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://accounts.spotify.com/api/token"
_API_BASE = "https://api.spotify.com/v1"

_token: str | None = None
_token_expiry: float = 0.0


def configured() -> bool:
    s = get_settings()
    return bool(s.spotify_client_id and s.spotify_client_secret)


async def _get_token(client: httpx.AsyncClient) -> str:
    global _token, _token_expiry
    if _token and time.time() < _token_expiry:
        return _token
    s = get_settings()
    if not (s.spotify_client_id and s.spotify_client_secret):
        raise RuntimeError(
            "SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET not configured "
            "(create a free app at developer.spotify.com/dashboard)"
        )
    resp = await client.post(
        _TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(s.spotify_client_id, s.spotify_client_secret),
    )
    resp.raise_for_status()
    data = resp.json()
    _token = data["access_token"]
    _token_expiry = time.time() + int(data.get("expires_in", 3600)) - 60
    return _token


async def get_track(track_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        token = await _get_token(client)
        resp = await client.get(
            f"{_API_BASE}/tracks/{track_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json()


async def get_album(album_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        token = await _get_token(client)
        resp = await client.get(
            f"{_API_BASE}/albums/{album_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json()


def extract_album_rights(album: dict) -> tuple[str | None, list[str]]:
    """(label, [copyright lines]) from an official album object."""
    label = album.get("label")
    copies = [
        c["text"] for c in album.get("copyrights") or [] if c.get("text")
    ]
    return label, copies
