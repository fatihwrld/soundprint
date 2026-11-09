# Soundprint 🎚️

**Open-source, self-hostable replacement for Spotify's deprecated Audio Features API — plus catalog intelligence (distributor detection).**

Spotify killed `/v1/audio-features` and `/v1/audio-analysis` in November 2024. Soundprint rebuilds them
from real signal analysis (Essentia / librosa) on 30-second previews fetched from public sources
(iTunes Search API, Deezer) — no Spotify API dependency, no proprietary ML mirroring.

## Why

- ReccoBeats: closed-source, unreliable, suspected Spotify-data mirroring
- FreqBlog / MeloData: commercial, closed
- AcousticBrainz: data collection stopped in 2022
- Essentia: great library, but you must build the whole service yourself

Soundprint = that service, open source, one `docker compose up`.

## Architecture

```
                ┌────────────────────────────┐
 track ID ─────►│  Resolution Layer          │
 ISRC ─────────►│  ID → ISRC → preview URL   │
 name+artist ──►└──────────────┬─────────────┘
                               │  iTunes Search API / Deezer (30s previews, no auth)
                               ▼
                ┌────────────────────────────┐
                │  Analysis Worker (RQ)      │
                │  Essentia / librosa DSP    │
                └──────────────┬─────────────┘
                               ▼
                ┌────────────────────────────┐
                │  Postgres catalog (ISRC PK)│
                └──────────────┬─────────────┘
                               ▼
   GET /v1/audio-features?ids=   (Spotify-compatible schema)
   GET /v1/lookup?track=&artist=
   GET /v1/distributor/{track}   (label/copyright → normalized distributor)
```

## Stack

| Layer | Tech |
|---|---|
| Front-end | Next.js 14 (App Router) + Tailwind CSS |
| API | FastAPI + pydantic v2 |
| DSP | Essentia (Docker) with librosa fallback |
| Queue | Redis + RQ |
| Storage | Postgres (ISRC primary key) |
| Infra | Docker Compose |

## Roadmap

- [x] M0 — spike: preview fetch → DSP → JSON (CLI + API stub)
- [ ] M1 — MVP: FastAPI + cache + Spotify-schema responses + Docker
- [ ] M2 — queue, batch lookups, dedup, rate limiting, CI
- [ ] M3 — MCP wrapper, Hugging Face parquet dataset, launch

## Running locally

### API

```bash
cd apps/api
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

### Web

```bash
cd apps/web
npm install
npm run dev
# → http://localhost:3000
```

### Full stack

```bash
docker compose up --build
```

## License

MIT (TBD)
