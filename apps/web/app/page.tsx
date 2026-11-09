import { SearchBar } from "@/components/search-bar";

const features = [
  {
    title: "Audio Features, yeniden inşa edildi",
    body: "Spotify'ın Kasım 2024'te öldürdüğü /v1/audio-features'ın açık kaynak muadili. Değerler gerçek sinyal analizinden (Essentia / librosa) geliyor — kopyalanmış veri değil.",
    tag: "DSP",
  },
  {
    title: "Distribütör istihbaratı",
    body: "Bir şarkının hangi distribütörle (DistroKid, TuneCore, Believe…) yayınlandığını label/copyright normalizasyonuyla tespit eder. Kimse bunu açık kaynak olarak sunmuyor.",
    tag: "Catalog",
  },
  {
    title: "Self-hosted, tek komut",
    body: "docker compose up — Postgres katalog, Redis kuyruk, FastAPI, Next.js. Veri sende kalır, ISRC anahtarlı temiz şema.",
    tag: "Infra",
  },
];

export default function Home() {
  return (
    <main className="relative mx-auto max-w-5xl px-6 pb-24 pt-20">
      {/* ambient glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-0 -z-10 h-[420px] w-[720px] -translate-x-1/2 rounded-full bg-cyan-500/10 blur-3xl"
      />

      <header className="flex flex-col items-center text-center">
        <span className="mb-5 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-xs text-cyan-300">
          open-source · self-hosted · MIT
        </span>
        <h1 className="bg-gradient-to-b from-white to-zinc-400 bg-clip-text text-5xl font-bold tracking-tight text-transparent sm:text-6xl">
          Soundprint
        </h1>
        <p className="mt-4 max-w-xl text-balance text-zinc-400">
          Spotify&apos;ın öldürdüğü Audio Features API&apos;nin açık kaynak muadili — ve
          distribütör tespiti. Gerçek DSP, gerçek katalog, sıfır kara kutu.
        </p>
      </header>

      <section className="mt-10 flex flex-col items-center">
        <SearchBar />
      </section>

      <section className="mt-20 grid gap-4 sm:grid-cols-3">
        {features.map((f) => (
          <div
            key={f.title}
            className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 transition hover:border-cyan-400/30 hover:bg-white/[0.05]"
          >
            <span className="font-mono text-[10px] uppercase tracking-wider text-cyan-300">
              {f.tag}
            </span>
            <h3 className="mt-2 font-semibold">{f.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-zinc-400">{f.body}</p>
          </div>
        ))}
      </section>

      <footer className="mt-20 border-t border-white/10 pt-6 text-center font-mono text-xs text-zinc-500">
        M0 spike · roadmap: MVP → queue &amp; batch → MCP + HuggingFace dataset
      </footer>
    </main>
  );
}
