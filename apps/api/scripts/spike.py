"""M0 spike: search -> preview -> DSP -> features, end to end.

Usage: .venv/Scripts/python scripts/spike.py "Blinding Lights" "The Weeknd"
"""

import asyncio
import sys

sys.path.insert(0, ".")

from app.analysis import engine
from app.services import preview as preview_svc


async def main() -> None:
    track = sys.argv[1]
    artist = sys.argv[2] if len(sys.argv) > 2 else None

    results = await preview_svc.search_itunes(track, artist)
    if not results:
        print("No results")
        return

    first = results[0]
    print(f"Track:   {first['track_name']} — {first['artist']}")
    print(f"Album:   {first['album']}")
    print(f"Preview: {first['preview_url']}")

    path = await engine.download_preview(first["preview_url"])
    try:
        features = engine.analyze_preview(path)
    finally:
        path.unlink(missing_ok=True)

    print("\n--- Audio Features (soundprint, real DSP) ---")
    for key, value in features.items():
        print(f"{key:>16}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
