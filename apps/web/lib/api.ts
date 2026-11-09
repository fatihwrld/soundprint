const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface LookupTrack {
  source: string;
  source_id: string;
  track_name: string;
  artist: string;
  album?: string;
  isrc?: string;
  preview_url?: string;
  artwork_url?: string;
}

export interface DistributorResult {
  distributor: string;
  category: "independent-aggregator" | "major" | "label-imprint" | "unknown";
  confidence: number;
  evidence: string[];
  label?: string | null;
  copyright_lines: string[];
}

export async function searchTracks(query: string): Promise<LookupTrack[]> {
  const res = await fetch(
    `${API_URL}/v1/lookup?track=${encodeURIComponent(query)}`,
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export async function fetchDistributor(spotifyId: string): Promise<DistributorResult> {
  const res = await fetch(`${API_URL}/v1/distributor/${spotifyId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}
