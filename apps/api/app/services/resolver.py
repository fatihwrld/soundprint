"""Resolution layer: any identifier → (metadata, ISRC, preview URL).

Inputs accepted:
- 22-char Spotify track ID → official catalog API → ISRC + name/artist
- ISRC → iTunes lookup by ISRC
- free text "track name [artist]" → iTunes/Deezer search
"""

import re

from app.services import preview as preview_svc
from app.services import spotify_catalog

_SPOTIFY_ID_RE = re.compile(r"^[A-Za-z0-9]{22}$")
_ISRC_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}\d{7}$")


class ResolvedTrack(dict):
    """keys: spotify_id, isrc, track_name, artist, album, preview_url, artwork_url, source"""


async def resolve(identifier: str) -> ResolvedTrack | None:
    identifier = identifier.strip()

    if _SPOTIFY_ID_RE.match(identifier):
        return await _resolve_spotify_id(identifier)

    if _ISRC_RE.match(identifier.upper()):
        result = await preview_svc.lookup_itunes_by_isrc(identifier.upper())
        if result:
            return ResolvedTrack(**result, spotify_id=None)
        return None

    # Free text: try "track artist" split heuristically
    results = await preview_svc.search_itunes(identifier)
    if results:
        return ResolvedTrack(**results[0])
    return None


async def _resolve_spotify_id(spotify_id: str) -> ResolvedTrack | None:
    if not spotify_catalog.configured():
        return None
    track = await spotify_catalog.get_track(spotify_id)
    isrc = (track.get("external_ids") or {}).get("isrc")
    artists = [a["name"] for a in track.get("artists") or []]
    name = track.get("name")
    artist = artists[0] if artists else None

    # 1) ISRC → iTunes (authoritative match)
    if isrc:
        itunes = await preview_svc.lookup_itunes_by_isrc(isrc)
        if itunes and itunes.get("preview_url"):
            return ResolvedTrack(
                **itunes, spotify_id=spotify_id, isrc=isrc,
                track_name=name, artist=artist,
            )

    # 2) name+artist search fallback
    for source in (preview_svc.search_itunes, preview_svc.search_deezer):
        try:
            results = await source(name, artist)
        except Exception:
            results = []
        for result in results:
            if result.get("preview_url"):
                return ResolvedTrack(
                    **result, spotify_id=spotify_id, isrc=isrc,
                    track_name=name, artist=artist,
                )
    return None
