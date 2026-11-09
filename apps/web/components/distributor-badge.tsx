"use client";

import { useEffect, useState } from "react";
import { fetchDistributor, type DistributorResult } from "@/lib/api";

const CATEGORY_STYLES: Record<DistributorResult["category"], string> = {
  major: "border-indigo-400/40 bg-indigo-400/10 text-indigo-300",
  "independent-aggregator": "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
  "label-imprint": "border-amber-400/40 bg-amber-400/10 text-amber-300",
  unknown: "border-white/10 bg-white/5 text-zinc-400",
};

export function DistributorBadge({ spotifyId }: { spotifyId: string }) {
  const [data, setData] = useState<DistributorResult | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    fetchDistributor(spotifyId)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [spotifyId]);

  if (failed) return null;
  if (!data) {
    return (
      <span className="h-5 w-16 animate-pulse rounded-full border border-white/10 bg-white/5" />
    );
  }
  if (data.distributor === "unknown") return null;

  return (
    <span
      title={
        data.evidence.length
          ? data.evidence.join(" · ")
          : data.label ?? ""
      }
      className={`inline-flex max-w-[220px] items-center gap-1 truncate rounded-full border px-2 py-0.5 text-[10px] font-medium ${CATEGORY_STYLES[data.category]}`}
    >
      {data.category === "major" && "🏷 "}
      {data.distributor}
    </span>
  );
}
