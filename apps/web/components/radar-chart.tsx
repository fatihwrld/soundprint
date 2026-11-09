"use client";

interface RadarChartProps {
  values: Partial<Record<string, number>>;
}

const AXES = [
  { key: "danceability", label: "Dance" },
  { key: "energy", label: "Energy" },
  { key: "speechiness", label: "Speech" },
  { key: "acousticness", label: "Acoustic" },
  { key: "instrumentalness", label: "Instr" },
  { key: "liveness", label: "Live" },
  { key: "valence", label: "Valence" },
];

const SIZE = 260;
const CENTER = SIZE / 2;
const RADIUS = 100;

function point(index: number, fraction: number) {
  const angle = (Math.PI * 2 * index) / AXES.length - Math.PI / 2;
  return {
    x: CENTER + Math.cos(angle) * RADIUS * fraction,
    y: CENTER + Math.sin(angle) * RADIUS * fraction,
  };
}

export function RadarChart({ values }: RadarChartProps) {
  const rings = [0.25, 0.5, 0.75, 1.0];
  const polygon = AXES.map((axis, i) => {
    const v = Math.max(0, Math.min(1, values[axis.key] ?? 0));
    const p = point(i, Math.max(v, 0.04));
    return `${p.x.toFixed(1)},${p.y.toFixed(1)}`;
  }).join(" ");

  return (
    <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} className="mx-auto">
      {rings.map((r) => (
        <polygon
          key={r}
          points={AXES.map((_, i) => {
            const p = point(i, r);
            return `${p.x},${p.y}`;
          }).join(" ")}
          fill="none"
          stroke="rgba(255,255,255,0.09)"
          strokeWidth={1}
        />
      ))}
      {AXES.map((axis, i) => {
        const p = point(i, 1);
        const lp = point(i, 1.18);
        return (
          <g key={axis.key}>
            <line
              x1={CENTER} y1={CENTER} x2={p.x} y2={p.y}
              stroke="rgba(255,255,255,0.09)" strokeWidth={1}
            />
            <text
              x={lp.x} y={lp.y}
              textAnchor="middle" dominantBaseline="middle"
              className="fill-zinc-400"
              style={{ fontSize: 10, fontFamily: "var(--font-geist-mono), monospace" }}
            >
              {axis.label}
            </text>
          </g>
        );
      })}
      <polygon
        points={polygon}
        fill="rgba(255,255,255,0.10)"
        stroke="rgba(255,255,255,0.65)"
        strokeWidth={1.5}
        strokeLinejoin="round"
      />
      {AXES.map((axis, i) => {
        const v = Math.max(0, Math.min(1, values[axis.key] ?? 0));
        const p = point(i, Math.max(v, 0.04));
        return <circle key={axis.key} cx={p.x} cy={p.y} r={3} fill="#0a84ff" />;
      })}
    </svg>
  );
}
