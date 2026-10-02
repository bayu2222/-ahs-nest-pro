import React from "react";
import { CheckCircle2, XCircle, ShieldCheck } from "lucide-react";

export default function SpacingVerification({ verification }) {
  const v = verification;
  const has = v && v.minDistance !== null && v.minDistance !== undefined;
  const pass = v?.pass;

  return (
    <div className="border border-[#262626] bg-[#141414] rounded-sm p-4" data-testid="spacing-verification">
      <div className="flex items-center justify-between mb-3">
        <div className="text-[11px] uppercase tracking-[0.2em] text-[#71717A] font-heading flex items-center gap-1.5">
          <ShieldCheck className="h-3.5 w-3.5" /> Spacing Verification
        </div>
        {v && (
          <span
            className="flex items-center gap-1 font-mono-data text-[11px] font-semibold px-2 py-0.5 rounded-sm border"
            style={{
              color: pass ? "#22C55E" : "#FF3B30",
              borderColor: pass ? "#22C55E66" : "#FF3B3066",
              background: pass ? "#22C55E14" : "#FF3B3014",
            }}
            data-testid="spacing-verdict"
          >
            {pass ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
            {pass ? "PASS" : "FAIL"}
          </span>
        )}
      </div>

      {!v ? (
        <p className="text-[11px] text-[#71717A] font-mono-data" data-testid="spacing-verification-empty">
          Run nesting to verify geometric spacing.
        </p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2">
            <div className="border border-[#262626] bg-[#0F0F0F] px-3 py-2.5" data-testid="verify-min-distance">
              <div className="text-[10px] uppercase tracking-[0.18em] text-[#71717A]">Min Distance</div>
              <div className="mt-1 flex items-baseline gap-1">
                <span
                  className="font-mono-data text-lg font-semibold leading-none"
                  style={{ color: pass ? "#22C55E" : "#FF3B30" }}
                >
                  {has ? v.minDistance.toFixed(4) : "—"}
                </span>
                <span className="font-mono-data text-[11px] text-[#71717A]">cm</span>
              </div>
            </div>
            <div className="border border-[#262626] bg-[#0F0F0F] px-3 py-2.5" data-testid="verify-violations">
              <div className="text-[10px] uppercase tracking-[0.18em] text-[#71717A]">Violating Pairs</div>
              <div className="mt-1 flex items-baseline gap-1">
                <span
                  className="font-mono-data text-lg font-semibold leading-none"
                  style={{ color: v.violatingPairs ? "#FF3B30" : "#22C55E" }}
                >
                  {v.violatingPairs}
                </span>
                <span className="font-mono-data text-[11px] text-[#71717A]">/ {v.pairsChecked}</span>
              </div>
            </div>
          </div>
          <p className="mt-3 text-[10px] leading-relaxed text-[#71717A] font-mono-data" data-testid="verify-note">
            Required ≥ {v.spacing.toFixed(2)} cm between every placed polygon ·
            measured with Shapely polygon distance (exact geometry, not bounding box).
          </p>
        </>
      )}
    </div>
  );
}
