"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { searchTracks, type LookupTrack } from "@/lib/api";
import { DistributorBadge } from "@/components/distributor-badge";
const SOURCE_LABELS: Record<string, string> = {
  spotify: "Spotify",
  itunes: "Apple",
  deezer: "Deezer",
};

export function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<LookupTrack[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const router = useRouter();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setStatus("loading");
    try {
      setResults(await searchTracks(query.trim()));
      setStatus("idle");
    } catch {
      setStatus("error");
      setResults([]);
    }
  }

  return (
    <div className="w-full max-w-2xl">
      <form onSubmit={onSubmit} className="flex gap-2.5">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Şarkı adı… örn. Blinding Lights"
          className="glass-input"
        />
        <button type="submit" disabled={status === "loading"} className="btn-primary">
          {status === "loading" ? "…" : "Search"}
        </button>
      </form>

      {status === "error" && (
        <p className="mt-3 text-center text-sm text-rose-400">
          API&apos;ye ulaşılamadı — apps/api çalışıyor mu?
        </p>
      )}

      <ul className="mt-5 space-y-2.5">
        {results.map((r) => (
          <li
            key={`${r.source}-${r.source_id}`}
            onClick={r.source === "spotify" ? () => router.push(`/track/${r.source_id}`) : undefined}
            className={`glass glass-hover flex items-center gap-3.5 !rounded-2xl p-3.5 ${r.source === "spotify" ? "cursor-pointer" : ""}`}
          >
            {r.artwork_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={r.artwork_url}
                alt=""
                className="h-11 w-11 rounded-[10px] shadow-lg shadow-black/40"
              />
            ) : (
              <div className="h-11 w-11 rounded-[10px] bg-white/10" />
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-zinc-100">{r.track_name}</p>
              <p className="truncate text-xs text-zinc-400">
                {r.artist} · {r.album}
              </p>
            </div>
            {r.source === "spotify" && <DistributorBadge spotifyId={r.source_id} />}
            <span className="glass-soft !rounded-full px-2.5 py-1 font-mono text-[10px] text-zinc-400">
              {SOURCE_LABELS[r.source] ?? r.source}
            </span>
            {r.preview_url && (
              <audio controls preload="none" src={r.preview_url} className="h-8 max-w-[170px]" />
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
