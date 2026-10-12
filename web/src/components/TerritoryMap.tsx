import type { Notable, Settlement } from "@/lib/types";

const TIER_RADIUS = [0, 5, 6.5, 8, 10];

export function TerritoryMap({
  width,
  height,
  settlements,
  notables,
}: {
  width: number;
  height: number;
  settlements: Settlement[];
  notables: Notable[];
}) {
  const w = Math.max(width, 1);
  const h = Math.max(height, 1);
  return (
    <div className="map-wrap">
      <svg className="map-svg" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="xMidYMid meet" role="img" aria-label="Carte des territoires">
        <defs>
          <radialGradient id="glow">
            <stop offset="0%" stopColor="#8b7cf6" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#8b7cf6" stopOpacity="0" />
          </radialGradient>
        </defs>
        {notables.map((n) => (
          <circle key={`n${n.id}`} cx={n.cell[0] + 0.5} cy={n.cell[1] + 0.5} r={1.1} fill="#5bb8f5" opacity={0.85} />
        ))}
        {settlements.map((s) => {
          const r = TIER_RADIUS[Math.min(s.tier, 4)] || 5;
          return (
            <g key={`s${s.id}`}>
              <circle cx={s.cell[0] + 0.5} cy={s.cell[1] + 0.5} r={r * 1.8} fill="url(#glow)" />
              <circle cx={s.cell[0] + 0.5} cy={s.cell[1] + 0.5} r={r * 0.45} fill="#f2b84b" stroke="#08090d" strokeWidth={0.5} />
              <text x={s.cell[0] + 0.5} y={s.cell[1] - r * 0.7} textAnchor="middle" fontSize={3.2} fill="#c4c9da" fontWeight={600}>
                {s.name}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="legend">
        <span>
          <i style={{ background: "#f2b84b" }} />
          Établissement
        </span>
        <span>
          <i style={{ background: "#5bb8f5" }} />
          Habitant notable
        </span>
        <span>
          Grille {width} × {height}
        </span>
      </div>
    </div>
  );
}
