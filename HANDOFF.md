# HANDOFF — yeni sohbet için proje durumu

Bu dosya, yeni bir AI oturumunun Soundprint'i kaldığı yerden devam etmesi içindir.

## Proje ne?
**Soundprint** — Spotify'ın Kasım 2024'te öldürdüğü `/v1/audio-features` + `/v1/audio-analysis` endpoint'lerinin açık kaynak, self-hostable muadili + distribütör istihbaratı (bir şarkının hangi distribütörle/DistroKid vs./ yayınlandığını label+copyright normalizasyonuyla tespit).
Repo: https://github.com/fatihwrld/soundprint (public, main, MIT, Fatih Kaya)

## Mimari (monorepo)
- `apps/api` — FastAPI (Python 3.15 venv, `.\.venv\Scripts\`)
  - `app/main.py` — endpoints: `/health`, `/v1/lookup` (Spotify+iTunes+Deezer birleşik, dedupe), `/v1/audio-features` (GET, comma ids; **POST `/v1/audio-features/batch`** 100 id limit), `/v1/distributor/{spotify_track_id}`
  - `app/api_guard.py` — API key (env `API_KEYS`, boş=açık mod) + IP başına rate limit (60/dk, 429+Retry-After)
  - `app/services/resolver.py` — Spotify ID → ISRC → iTunes ISRC lookup → name search fallback
  - `app/services/preview.py` — iTunes Search API + Deezer + resmi Spotify search (preview URL toplama)
  - `app/services/spotify_catalog.py` — Client Credentials; **429'da Retry-After'a saygılı retry (max 60s, 4 deneme)**
  - `app/services/distributor.py` — 20+ distribütör alias tablosu + major imprint haritası (Republic→UMG vs.)
  - `app/analysis/engine.py` — **İki katmanlı**: `raw_descriptors` (librosa; tempo oktav düzeltmesi log-normal prior + beat-grid support testi ile) → `map_features` (varsa `calibration.json` eğrileri, yoksa heuristics). `analyzer` alanı: `librosa-calibrated` / `librosa-heuristic`
  - `app/analysis/calibration.json` — FIT EDİLMİŞ KALİBRASYON (n=98, isotonic eğriler + tempo_scale 1.0 + loudness affine). Kaynak dataset: maharshipandya/spotify-tracks-dataset (114k, BSD; 20MB CSV `apps/api/scripts/dataset.csv`, GİTİGNORE'LU)
  - `app/db.py` — SQLAlchemy 2.0, varsayılan SQLite `soundprint.db`; `DATABASE_URL` env ile Postgres'e geçer. Tablo: `feature_cache` (ISRC anahtarlı)
  - `scripts/calibrate.py`, `scripts/validate.py` — yeniden fit + bilinen şarkılarla doğrulama
- `apps/web` — Next.js 16.4.5 + React 19 + Tailwind 3.4, Apple glassmorphism siyah tema (`.glass`/`.glass-soft`/`.btn-primary` utility'leri `globals.css`'te)
  - Arama → Spotify satırlarında DistributorBadge → `/track/[id]` detay (radar chart SVG + feature barları + tempo/key stats + distribütör)

## Çalıştırma
```powershell
# API (PATH: python + winget links kalıcı eklendi)
cd C:\Users\Administrator\Projects\soundprint\apps\api
.\.venv\Scripts\uvicorn app.main:app --reload
# Web
cd ..\web; npm run dev
# ffmpeg PATH'te (WinGet Links); Spotify creds `apps/api/.env`'de (gitignored)
```

## Doğrulanmış doğruluk (out-of-sample)
Blinding Lights vs Spotify gerçekleri: tempo 172.27 vs 171.005 (Δ1.27), energy Δ0.032, valence Δ0.027, danceability Δ0.099. Zayıf taraf: acousticness/instrumentalness eğrileri sıfıra basamıyor; akustik/eski kayıtlarda energy yüksek çıkıyor (RMS proxy sınırı). "Yesterday" testi zayıf.

## Sıradaki işler (öncelik sırasıyla)
1. **Pairs persistence + kalibrasyon v2**: `calibrate.py` çiftleri `scripts/calibration_pairs.json`'a kümülatif yazsın (429'a rağmen ilerleme korunur); sonra 1-D isotonic yerine çok değişkenli (GradientBoosting) fit + HPSS (harmonic/percussive) descriptor'lar ekle
2. **Docker Desktop kur** (winget `Docker.DockerDesktop`) → compose up → `DATABASE_URL=postgres://...` ile Postgres + Redis/RQ kuyruğu (analiz async)
3. **Rate limit durumuna dikkat**: Spotify Client Credentials 429 veriyor; kalibrasyon toplamak için retry'a saygılı davran (zaten kodda), 0.3-1 sn sleep
4. **M3**: HuggingFace'e parquet dataset release + MCP server wrapper + Show HN / r/spotifyapi lansmanı
5. Front-end: itunes/deezer satırları için de analiz sayfası (isim→ISRC çözümüyle)

## Konvansiyonlar
- Commit mesajları İngilizce, tek satır; özellik dosyalarında Türkçe yorumlar serbest
- Testler: TestClient ile hızlı doğrulama (git commit öncesi web build `npm run build` + API smoke test)
- Git kimliği global config'te (Fatih Kaya). `gh` CLI yüklü ve otantike (fatihwrld)
- Dağıtım yok, hepsi local Windows; PATH kalıcı düzeltildi (python315, nodejs, git, winget links)
