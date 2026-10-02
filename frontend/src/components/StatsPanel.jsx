import React from "react";

function Stat({ label, value, unit, accent, testid }) {
  return (
    <div className="border border-[#262626] bg-[#0F0F0F] px-3 py-2.5" data-testid={testid}>
      <div className="text-[10px] uppercase tracking-[0.18em] text-[#71717A]">{label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span
          className="font-mono-data text-lg font-semibold leading-none"
          style={{ color: accent || "#FFFFFF" }}
        >
          {value}
        </span>
        {unit && <span className="font-mono-data text-[11px] text-[#71717A]">{unit}</span>}
      </div>
    </div>
  );
}

export default function StatsPanel({ stats }) {
  const s = stats || {};
  const n = (v, d = 2) => (v === undefined || v === null ? "—" : Number(v).toFixed(d));
  const util = s.utilization;
  const utilColor = util >= 70 ? "#22C55E" : util >= 50 ? "#EAB308" : "#FF3B30";

  return (
    <div className="grid grid-cols-2 gap-2" data-testid="stats-panel">
      <Stat label="Utilization" value={util === undefined ? "—" : n(util, 1)} unit="%" accent={utilColor} testid="stat-utilization" />
      <Stat label="Used Height" value={n(s.usedHeight, 2)} unit="cm" testid="stat-used-height" />
      <Stat label="Used Width" value={n(s.usedWidth, 2)} unit="cm" testid="stat-used-width" />
      <Stat label="Media Width" value={n(s.mediaWidth, 1)} unit="cm" accent="#38BDF8" testid="stat-media-width" />
      <Stat label="Objects" value={s.objectCount ?? "—"} testid="stat-object-count" />
      <Stat label="Placed" value={s.placedCount ?? "—"} accent="#22C55E" testid="stat-placed-count" />
      <Stat label="Failed" value={s.failedPlacements ?? "—"} accent={s.failedPlacements ? "#FF3B30" : "#71717A"} testid="stat-failed" />
      <Stat label="Candidates" value={s.candidatesTested ?? "—"} testid="stat-candidates" />
      <Stat label="Proc. Time" value={s.processingTime === undefined ? "—" : (s.processingTime * 1000).toFixed(1)} unit="ms" accent="#007AFF" testid="stat-proc-time" />
      <Stat label="Algorithm" value={s.algorithm ? "BLF" : "—"} testid="stat-algorithm" />
    </div>
  );
}
