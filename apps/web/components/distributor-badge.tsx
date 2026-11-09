"use client";

import { useEffect, useState } from "react";
import { fetchDistributor, type DistributorResult } from "@/lib/api";

const CATEGORY_STYLES: Record<DistributorResult["category"], string> = {
  major: "text-indigo-300 border-indigo-300/25",
  "independent-aggregator": "text-emerald-300 border-emerald-300/25",
  "label-imprint": "text-amber-300 border-amber-300/25",
  unknown: "text-zinc-500 border-white/10",
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
      <span className="glass-soft h-5 w-16 animate-pulse !rounded-full" />
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
      className={`glass-soft inline-flex max-w-[220px] items-center gap-1 truncate !rounded-full px-2.5 py-1 text-[10px] font-medium ${CATEGORY_STYLES[data.category]}`}
    >
      {data.category === "major" && "🏷 "}
      {data.distributor}
    </span>
  );
}
