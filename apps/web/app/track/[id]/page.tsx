"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { fetchDistributor, type DistributorResult, API_URL } from "@/lib/api";
import { RadarChart } from "@/components/radar-chart";

const KEY_NAMES = ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"];

const BARS: { key: string; label: string }[] = [
  { key: "danceability", label: "Danceability" },
  { key: "energy", label: "Energy" },
  { key: "speechiness", label: "Speechiness" },
  { key: "acousticness", label: "Acousticness" },
  { key: "instrumentalness", label: "Instrumentalness" },
  { key: "liveness", label: "Liveness" },
  { key: "valence", label: "Valence" },
];

interface Features {
  id: string;
  isrc?: string | null;
  track_name?: string | null;
  artist?: string | null;
  analyzer?: string;
  tempo: number;
  loudness: number;
  key: number;
  mode: number;
  time_signature: number;
  danceability: number;
  energy: number;
  speechiness: number;
  acousticness: number;
  instrumentalness: number;
  liveness: number;
  valence: number;
}

export default function TrackPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [features, setFeatures] = useState<Features | null>(null);
  const [distributor, setDistributor] = useState<DistributorResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    fetch(`${API_URL}/v1/audio-features?ids=${encodeURIComponent(String(id))}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`API ${res.status}`);
        const data = await res.json();
        setFeatures(data[0]);
      })
      .catch((e) => setError(String(e)));
    fetchDistributor(String(id))
      .then(setDistributor)
      .catch(() => setDistributor(null));
  }, [id]);

  if (error) {
    return (
      <main className="glass mx-auto mt-24 max-w-md p-8 text-center">
        <p className="text-sm text-rose-400">Analiz başarısız: {error}</p>
        <button onClick={() => router.back()} className="btn-primary mt-6">← Back</button>
      </main>
    );
  }

  return (
    <main className="relative mx-auto max-w-3xl px-6 pb-24 pt-14">
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="aurora left-[20%] top-[-120px] h-[360px] w-[480px] bg-white/[0.06]" />
        <div className="aurora right-[10%] top-[220px] h-[320px] w-[320px] bg-[#0a84ff]/[0.10]" />
      </div>

      <Link
        href="/"
        className="glass-soft inline-flex items-center gap-1.5 !rounded-full px-4 py-2 text-xs text-zinc-300 hover:!bg-white/[0.08]"
      >
        ← Search
      </Link>

      <header className="mt-8 text-center">
        <h1 className="text-4xl font-semibold tracking-tight">
          {features?.track_name ?? (features ? <span className="text-zinc-500">Unknown track</span> : "Analyzing…")}
        </h1>
        <p className="mt-2 text-sm text-zinc-400">{features?.artist ?? ""}</p>
        {distributor && distributor.distributor !== "unknown" && (
          <p className="mt-3 inline-flex glass-soft !rounded-full items-center gap-1.5 px-3.5 py-1.5 text-xs">
            <span className="text-zinc-500">Distributed via</span>
            <span className={
              distributor.category === "major" ? "text-indigo-300" : "text-emerald-300"
            }>
              {distributor.distributor}
            </span>
          </p>
        )}
      </header>

      {features ? (
        <>
          <section className="glass mt-10 grid grid-cols-2 gap-4 p-6 sm:grid-cols-4">
            <Stat label="Tempo" value={`${features.tempo.toFixed(1)} BPM`} />
            <Stat label="Key" value={`${KEY_NAMES[features.key] ?? features.key} ${features.mode === 1 ? "maj" : "min"}`} />
            <Stat label="Loudness" value={`${features.loudness.toFixed(1)} dB`} />
            <Stat label="Time sig" value={`${features.time_signature}/4`} />
          </section>

          <section className="glass mt-6 flex flex-col items-center gap-6 p-8 sm:flex-row">
            <RadarChart
              values={{
                danceability: features.danceability,
                energy: features.energy,
                speechiness: features.speechiness,
                acousticness: features.acousticness,
                instrumentalness: features.instrumentalness,
                liveness: features.liveness,
                valence: features.valence,
              }}
            />
            <div className="w-full flex-1 space-y-3">
              {BARS.map((b) => (
                <div key={b.key}>
                  <div className="mb-1 flex justify-between text-xs">
                    <span className="text-zinc-400">{b.label}</span>
                    <span className="font-mono text-zinc-200">
                      {(features[b.key as keyof Features] as number).toFixed(2)}
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-zinc-300 to-white"
                      style={{ width: `${Math.min(100, (features[b.key as keyof Features] as number) * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="mt-6 flex flex-wrap justify-center gap-2.5 text-[11px]">
            <Chip label={`ISRC ${features.isrc ?? "—"}`} />
            <Chip label={`analyzer: ${features.analyzer ?? "—"}`} />
            <Chip label={`id: ${features.id.slice(0, 12)}…`} />
            {distributor?.evidence.length ? (
              <Chip label={distributor.evidence[0].slice(0, 90)} />
            ) : null}
          </section>
        </>
      ) : (
        <div className="glass mt-10 p-10 text-center text-sm text-zinc-400">
          DSP pipeline çalışıyor… (30 sn preview → ffmpeg → librosa)
        </div>
      )}
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <p className="text-[11px] uppercase tracking-[0.12em] text-zinc-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-zinc-100">{value}</p>
    </div>
  );
}

function Chip({ label }: { label: string }) {
  return (
    <span className="glass-soft !rounded-full px-3 py-1.5 font-mono text-zinc-400">
      {label}
    </span>
  );
}
