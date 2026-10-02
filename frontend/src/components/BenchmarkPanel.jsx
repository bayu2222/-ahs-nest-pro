import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Gauge, Loader2 } from "lucide-react";

const PRESET = [10, 20, 50, 100];

export default function BenchmarkPanel({ onRun, results, busy, settings }) {
  const [selected, setSelected] = useState([10, 20, 50]);

  const toggle = (c) =>
    setSelected((s) => (s.includes(c) ? s.filter((x) => x !== c) : [...s, c].sort((a, b) => a - b)));

  return (
    <div className="space-y-4" data-testid="benchmark-panel">
      <div className="flex items-center justify-between">
        <div className="text-[11px] uppercase tracking-[0.2em] text-[#71717A] font-heading">Benchmark Sets</div>
        <span className="font-mono-data text-[10px] text-[#52525B]">
          seed · rot {settings.rotationStep}°
        </span>
      </div>

      <div className="grid grid-cols-4 gap-1.5">
        {PRESET.map((c) => (
          <button
            key={c}
            onClick={() => toggle(c)}
            className={`h-8 rounded-sm border font-mono-data text-xs transition-colors duration-100 ${
              selected.includes(c)
                ? "border-[#007AFF] bg-[#007AFF]/15 text-white"
                : "border-[#262626] bg-[#0F0F0F] text-[#A1A1AA] hover:border-[#3a3a3a]"
            }`}
            data-testid={`benchmark-preset-${c}`}
          >
            {c}
          </button>
        ))}
      </div>

      <Button
        className="w-full h-9 rounded-sm bg-[#EAB308] hover:bg-[#f5c324] text-black font-medium transition-colors duration-100 disabled:opacity-50"
        onClick={() => onRun(selected)}
        disabled={busy || selected.length === 0}
        data-testid="btn-run-benchmark"
      >
        {busy ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Gauge className="h-4 w-4 mr-2" />}
        {busy ? "Benchmarking…" : "Run Benchmark"}
      </Button>

      {results && results.length > 0 && (
        <div className="border border-[#262626] overflow-hidden" data-testid="benchmark-results">
          <table className="w-full font-mono-data text-[11px]">
            <thead>
              <tr className="bg-[#0F0F0F] text-[#71717A] text-[9px] uppercase tracking-wider">
                <th className="px-2 py-1.5 text-left">N</th>
                <th className="px-2 py-1.5 text-right">Time</th>
                <th className="px-2 py-1.5 text-right">Height</th>
                <th className="px-2 py-1.5 text-right">Util%</th>
                <th className="px-2 py-1.5 text-right">Fail</th>
                <th className="px-2 py-1.5 text-right">Cand.</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.objectCount} className="border-t border-[#1f1f1f] text-[#D4D4D8]" data-testid={`benchmark-row-${r.objectCount}`}>
                  <td className="px-2 py-1.5 text-white">{r.objectCount}</td>
                  <td className="px-2 py-1.5 text-right text-[#007AFF]">{(r.processingTime * 1000).toFixed(0)}ms</td>
                  <td className="px-2 py-1.5 text-right">{r.usedHeight.toFixed(1)}</td>
                  <td className="px-2 py-1.5 text-right" style={{ color: r.utilization >= 65 ? "#22C55E" : "#EAB308" }}>
                    {r.utilization.toFixed(1)}
                  </td>
                  <td className="px-2 py-1.5 text-right" style={{ color: r.failedPlacements ? "#FF3B30" : "#52525B" }}>
                    {r.failedPlacements}
                  </td>
                  <td className="px-2 py-1.5 text-right text-[#71717A]">{r.candidatesTested}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
