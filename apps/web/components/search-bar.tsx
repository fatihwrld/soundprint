"use client";

import { useState } from "react";
import { searchTracks, type LookupTrack } from "@/lib/api";

export function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<LookupTrack[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");

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
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Track name… e.g. Blinding Lights"
          className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none placeholder:text-zinc-500 focus:border-cyan-400/50 focus:ring-2 focus:ring-cyan-400/20"
        />
        <button
          type="submit"
          disabled={status === "loading"}
          className="rounded-xl bg-gradient-to-b from-cyan-400 to-cyan-500 px-5 py-3 text-sm font-semibold text-cyan-950 transition hover:brightness-110 disabled:opacity-50"
        >
          {status === "loading" ? "…" : "Search"}
        </button>
      </form>

      {status === "error" && (
        <p className="mt-3 text-sm text-rose-400">
          API'ye ulaşılamadı — apps/api çalışıyor mu? (uvicorn app.main:app --reload)
        </p>
      )}

      <ul className="mt-4 space-y-2">
        {results.map((r) => (
          <li
            key={`${r.source}-${r.source_id}`}
            className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3"
          >
            {r.artwork_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={r.artwork_url} alt="" className="h-10 w-10 rounded-md" />
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{r.track_name}</p>
              <p className="truncate text-xs text-zinc-400">
                {r.artist} · {r.album}
              </p>
            </div>
            <span className="rounded-full border border-white/10 px-2 py-0.5 font-mono text-[10px] uppercase text-zinc-400">
              {r.source}
            </span>
            {r.preview_url && (
              <audio controls preload="none" src={r.preview_url} className="h-8 max-w-[180px]" />
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
