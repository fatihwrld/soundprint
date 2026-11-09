"""Validate calibration against Spotify's published real values.

Usage: .venv/Scripts/python scripts/validate.py
"""

import asyncio
import json
import sys

sys.path.insert(0, ".")

from app.analysis import engine
from app.db import engine as db_engine
from app.services import preview as preview_svc
from sqlalchemy import text

KNOWN = [
    {  # Spotify's real pre-deprecation values (widely published)
        "spotify_id": "0VjIjW4GlUZAMYd2vXMi3b",
        "name": "Blinding Lights",
        "artist": "The Weeknd",
        "features": {
            "danceability": 0.514, "energy": 0.802, "speechiness": 0.0624,
            "acousticness": 0.00488, "instrumentalness": 3.31e-06,
            "liveness": 0.0988, "valence": 0.515, "tempo": 171.005,
            "loudness": -5.986,
        },
    },
    {
        "spotify_id": "0jiV0bjqLik2nYRxDfZkgW",
        "name": "Yesterday",
        "artist": "The Beatles",
        "features": {
            "danceability": 0.19, "energy": 0.274, "speechiness": 0.0457,
            "acousticness": 0.878, "instrumentalness": 0.000148,
            "liveness": 0.0913, "valence": 0.187, "tempo": 73.69,
            "loudness": -13.299,
        },
    },
]


async def main() -> None:
    cal = engine.load_calibration()
    print("CALIBRATION LOADED:", bool(cal), "| n_tracks:", cal["n_tracks"] if cal else None)

    # stale (pre-calibration) cache temizle
    with db_engine.begin() as conn:
        conn.execute(text("DELETE FROM feature_cache"))

    for ref in KNOWN:
        # Spotify API rate limitinden kaçınmak için preview'ı iTunes'tan al
        results = await preview_svc.search_itunes(ref["name"], ref["artist"])
        results = [r for r in results if r.get("preview_url")]
        # en uzun süreli / ilk sonuç: aynı isimli cover'ları ayıklamak için
        # sanatçı adı eşleşmesine öncelik ver
        def _score(r):
            artist_match = ref["artist"].lower() in str(r.get("artist") or "").lower()
            return (artist_match, r.get("album") or "")
        results.sort(key=_score, reverse=True)
        if not results:
            print(f"\n{ref['name']}: no preview found, skipping")
            continue
        first = results[0]

        path = await engine.download_preview(first["preview_url"])
        try:
            data = engine.analyze_preview(path)
        finally:
            path.unlink(missing_ok=True)

        print(f"\n=== {ref['name']} — {ref['artist']} | preview: {first['artist']} | analyzer: {data.get('analyzer')} ===")
        print(f"{'feature':>18} | {'soundprint':>10} | {'Spotify':>9} | diff")
        print("-" * 55)
        for key, target in ref["features"].items():
            ours = data[key]
            print(f"{key:>18} | {ours:>10.4f} | {target:>9.4f} | {abs(ours - target):.4f}")


if __name__ == "__main__":
    asyncio.run(main())
