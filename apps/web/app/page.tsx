import { SearchBar } from "@/components/search-bar";

const features = [
  {
    title: "Audio Features, rebuilt",
    body: "Spotify'ın Kasım 2024'te öldürdüğü /v1/audio-features'ın açık kaynak muadili. Değerler gerçek sinyal analizinden geliyor — kopyalanmış veri değil.",
    tag: "DSP",
  },
  {
    title: "Distributor intelligence",
    body: "Bir şarkının hangi distribütörle yayınlandığını label/copyright normalizasyonuyla tespit eder. Kimse bunu açık kaynak olarak sunmuyor.",
    tag: "Catalog",
  },
  {
    title: "Self-hosted, one command",
    body: "docker compose up — Postgres katalog, Redis kuyruk, FastAPI, Next.js. Veri sende kalır, ISRC anahtarlı temiz şema.",
    tag: "Infra",
  },
];

export default function Home() {
  return (
    <main className="relative mx-auto max-w-5xl px-6 pb-24 pt-24">
      {/* ambient aurora — black base, subtle light */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div
          className="aurora left-[8%] top-[-140px] h-[420px] w-[520px] bg-white/[0.07]"
        />
        <div
          className="aurora right-[4%] top-[120px] h-[380px] w-[380px] bg-[#0a84ff]/[0.12]"
        />
        <div
          className="aurora left-[30%] top-[420px] h-[300px] w-[560px] bg-white/[0.04]"
        />
      </div>

      <header className="flex flex-col items-center text-center">
        <span className="glass-soft mb-6 rounded-full px-4 py-1.5 font-mono text-[11px] tracking-wide text-zinc-300">
          open-source · self-hosted · MIT
        </span>
        <h1 className="bg-gradient-to-b from-white via-white to-zinc-400 bg-clip-text text-6xl font-semibold tracking-tight text-transparent sm:text-7xl">
          Soundprint
        </h1>
        <p className="mt-5 max-w-xl text-balance text-[15px] leading-relaxed text-zinc-400">
          Spotify&apos;ın öldürdüğü Audio Features API&apos;nin açık kaynak muadili — ve
          distribütör tespiti. Gerçek DSP, gerçek katalog, sıfır kara kutu.
        </p>
      </header>

      <section className="mt-12 flex flex-col items-center">
        <SearchBar />
      </section>

      <section className="mt-24 grid gap-5 sm:grid-cols-3">
        {features.map((f) => (
          <div
            key={f.title}
            className="glass glass-hover p-6"
          >
            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-[#64a8ff]">
              {f.tag}
            </span>
            <h3 className="mt-3 text-[15px] font-semibold text-zinc-100">{f.title}</h3>
            <p className="mt-2 text-[13px] leading-relaxed text-zinc-400">{f.body}</p>
          </div>
        ))}
      </section>

      <footer className="mt-24 border-t border-white/10 pt-6 text-center font-mono text-[11px] text-zinc-500">
        M2 · roadmap: calibration → queue &amp; batch → MCP + HuggingFace dataset
      </footer>
    </main>
  );
}
