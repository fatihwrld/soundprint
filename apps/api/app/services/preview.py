"""Preview resolution: find a 30-second preview URL for a track.

Sources (no auth, no Spotify API):
- iTunes Search API: ISRC lookup + term search (m4a previews)
- Deezer public API: term search (mp3 previews)

ISRC note: iTunes lookup supports `?isrc=...` directly.
"""

import httpx

ITUNES_BASE = "https://itunes.apple.com"
DEEZER_BASE = "https://api.deezer.com"

_UA = {"User-Agent": "soundprint/0.1 (open-source audio features service)"}


async def _get_json(client: httpx.AsyncClient, url: str, params: dict | None = None):
    resp = await client.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


async def lookup_itunes_by_isrc(isrc: str) -> dict | None:
    async with httpx.AsyncClient(headers=_UA, follow_redirects=True) as client:
        data = await _get_json(client, f"{ITUNES_BASE}/lookup", {"isrc": isrc, "entity": "song"})
    for result in data.get("results", []):
        if result.get("wrapperType") == "track":
            return _normalize_itunes(result)
    return None


async def search_itunes(track: str, artist: str | None = None) -> list[dict]:
    term = f"{artist} {track}" if artist else track
    async with httpx.AsyncClient(headers=_UA, follow_redirects=True) as client:
        data = await _get_json(
            client, f"{ITUNES_BASE}/search", {"term": term, "entity": "song", "limit": 10}
        )
    return [_normalize_itunes(r) for r in data.get("results", []) if r.get("wrapperType") == "track"]


async def search_deezer(track: str, artist: str | None = None) -> list[dict]:
    query = f'artist:"{artist}" track:"{track}"' if artist else f'track:"{track}"'
    async with httpx.AsyncClient(headers=_UA, follow_redirects=True) as client:
        data = await _get_json(client, f"{DEEZER_BASE}/search", {"q": query, "limit": 10})
    return [
        {
            "source": "deezer",
            "source_id": str(item["id"]),
            "track_name": item["title"],
            "artist": item["artist"]["name"],
            "album": item["album"]["title"],
            "isrc": None,
            "preview_url": item.get("preview") or None,
            "artwork_url": item.get("album", {}).get("cover_medium"),
        }
        for item in data.get("data", [])
    ]


def _normalize_itunes(result: dict) -> dict:
    return {
        "source": "itunes",
        "source_id": str(result["trackId"]),
        "track_name": result.get("trackName"),
        "artist": result.get("artistName"),
        "album": result.get("collectionName"),
        "isrc": None,  # iTunes search does not return ISRC; lookup?isrc= does
        "preview_url": result.get("previewUrl"),
        "artwork_url": result.get("artworkUrl100"),
    }


async def search_spotify(track: str, artist: str | None = None) -> list[dict]:
    """Official Web API search via Client Credentials (public catalog)."""
    import asyncio
    import time

    from app.services import spotify_catalog

    if not spotify_catalog.configured():
        return []
    query = f"track:{track}" + (f" artist:{artist}" if artist else "")
    async with httpx.AsyncClient() as client:
        token = await spotify_catalog._get_token(client)
        resp = await client.get(
            "https://api.spotify.com/v1/search",
            params={"q": query, "type": "track", "limit": 10},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()
    results = []
    for item in data.get("tracks", {}).get("items", []):
        images = (item.get("album") or {}).get("images") or []
        results.append({
            "source": "spotify",
            "source_id": item["id"],
            "track_name": item.get("name"),
            "artist": ", ".join(a["name"] for a in item.get("artists") or []),
            "album": (item.get("album") or {}).get("name"),
            "isrc": None,
            "preview_url": item.get("preview_url"),
            "artwork_url": images[0]["url"] if images else None,
        })
    return results
