import React from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Play, Shuffle, Eraser, RotateCcw, Loader2 } from "lucide-react";
import SvgImportPanel from "@/components/SvgImportPanel";

function Field({ label, children, hint }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label className="text-[10px] uppercase tracking-[0.18em] text-[#A1A1AA]">{label}</label>
        {hint && <span className="font-mono-data text-[10px] text-[#52525B]">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

const inputCls =
  "h-9 rounded-sm bg-[#0F0F0F] border-[#262626] text-white font-mono-data text-sm focus-visible:ring-1 focus-visible:ring-[#007AFF] focus-visible:border-[#007AFF]";

function Toggle({ label, color, checked, onChange, testid }) {
  return (
    <label className="flex items-center justify-between py-1 cursor-pointer" data-testid={testid}>
      <span className="flex items-center gap-2 text-xs text-[#D4D4D8]">
        <span className="h-2.5 w-2.5 rounded-[1px]" style={{ background: color }} />
        {label}
      </span>
      <Switch checked={checked} onCheckedChange={onChange} className="data-[state=checked]:bg-[#007AFF]" />
    </label>
  );
}

export default function ControlPanel({
  settings,
  setSettings,
  count,
  setCount,
  onGenerate,
  onNest,
  onClear,
  onReset,
  busy,
  hasObjects,
  debug,
  setDebug,
  source,
  setSource,
  svgImport,
  onImportSvg,
}) {
  const update = (k, v) => setSettings((s) => ({ ...s, [k]: v }));
  const num = (v, fb) => (v === "" || isNaN(Number(v)) ? fb : Number(v));

  return (
    <div className="space-y-5" data-testid="control-panel">
      {/* media */}
      <div className="space-y-3">
        <div className="text-[11px] uppercase tracking-[0.2em] text-[#71717A] font-heading">Media</div>
        <Field label="Width" hint="cm">
          <Input
            type="number"
            className={inputCls}
            value={settings.mediaWidth}
            min={10}
            step={1}
            onChange={(e) => update("mediaWidth", num(e.target.value, 120))}
            data-testid="input-media-width"
          />
        </Field>
        <div className="grid grid-cols-2 gap-1.5">
          <button
            className={`h-8 rounded-sm border text-[11px] uppercase tracking-wider transition-colors duration-100 ${
              settings.heightMode === "auto"
                ? "border-[#007AFF] bg-[#007AFF]/15 text-white"
                : "border-[#262626] bg-[#0F0F0F] text-[#A1A1AA] hover:border-[#3a3a3a]"
            }`}
            onClick={() => update("heightMode", "auto")}
            data-testid="btn-height-auto"
          >
            Auto Height
          </button>
          <button
            className={`h-8 rounded-sm border text-[11px] uppercase tracking-wider transition-colors duration-100 ${
              settings.heightMode === "fixed"
                ? "border-[#007AFF] bg-[#007AFF]/15 text-white"
                : "border-[#262626] bg-[#0F0F0F] text-[#A1A1AA] hover:border-[#3a3a3a]"
            }`}
            onClick={() => update("heightMode", "fixed")}
            data-testid="btn-height-fixed"
          >
            Fixed Height
          </button>
        </div>
        {settings.heightMode === "fixed" && (
          <Field label="Height" hint="cm">
            <Input
              type="number"
              className={inputCls}
              value={settings.mediaHeight}
              min={10}
              step={1}
              onChange={(e) => update("mediaHeight", num(e.target.value, 100))}
              data-testid="input-media-height"
            />
          </Field>
        )}
      </div>

      <Separator className="bg-[#262626]" />

      {/* constraints */}
      <div className="space-y-3">
        <div className="text-[11px] uppercase tracking-[0.2em] text-[#71717A] font-heading">Constraints</div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Spacing" hint="cm">
            <Input
              type="number"
              className={inputCls}
              value={settings.spacing}
              min={0}
              step={0.1}
              onChange={(e) => update("spacing", num(e.target.value, 0.3))}
              data-testid="input-spacing"
            />
          </Field>
          <Field label="Rot. Step" hint="deg">
            <Input
              type="number"
              className={inputCls}
              value={settings.rotationStep}
              min={0}
              step={0.5}
              onChange={(e) => update("rotationStep", num(e.target.value, 5))}
              data-testid="input-rotation-step"
            />
          </Field>
        </div>
        <label className="flex items-center justify-between py-1 cursor-pointer" data-testid="toggle-allow-rotation">
          <span className="text-xs text-[#D4D4D8]">Allow rotation (0–360°)</span>
          <Switch
            checked={settings.allowRotation}
            onCheckedChange={(v) => update("allowRotation", v)}
            className="data-[state=checked]:bg-[#007AFF]"
          />
        </label>
      </div>

      <Separator className="bg-[#262626]" />

      {/* objects */}
      <div className="space-y-3">
        <div className="text-[11px] uppercase tracking-[0.2em] text-[#71717A] font-heading">Objects</div>
        <Field label="Source">
          <div className="grid grid-cols-2 gap-1.5">
            <button
              className={`h-8 rounded-sm border text-[11px] uppercase tracking-wider transition-colors duration-100 ${
                source === "random"
                  ? "border-[#007AFF] bg-[#007AFF]/15 text-white"
                  : "border-[#262626] bg-[#0F0F0F] text-[#A1A1AA] hover:border-[#3a3a3a]"
              }`}
              onClick={() => setSource("random")}
              disabled={busy}
              data-testid="btn-source-random"
            >
              Random Test
            </button>
            <button
              className={`h-8 rounded-sm border text-[11px] uppercase tracking-wider transition-colors duration-100 ${
                source === "svg"
                  ? "border-[#007AFF] bg-[#007AFF]/15 text-white"
                  : "border-[#262626] bg-[#0F0F0F] text-[#A1A1AA] hover:border-[#3a3a3a]"
              }`}
              onClick={() => setSource("svg")}
              disabled={busy}
              data-testid="btn-source-svg"
            >
              Imported SVG
            </button>
          </div>
        </Field>

        {source === "random" ? (
          <>
            <Field label="Random count">
              <Input
                type="number"
                className={inputCls}
                value={count}
                min={1}
                max={300}
                step={1}
                onChange={(e) => setCount(num(e.target.value, 20))}
                data-testid="input-object-count"
              />
            </Field>
            <Button
              variant="outline"
              className="w-full h-9 rounded-sm border-[#262626] bg-[#0F0F0F] text-[#E4E4E7] hover:bg-[#1a1a1a] hover:text-white transition-colors duration-100"
              onClick={onGenerate}
              disabled={busy}
              data-testid="btn-generate"
            >
              <Shuffle className="h-3.5 w-3.5 mr-2" /> Generate Objects
            </Button>
          </>
        ) : (
          <SvgImportPanel svgImport={svgImport} onImportSvg={onImportSvg} disabled={busy} />
        )}

        {hasObjects > 0 && (
          <div className="font-mono-data text-[11px] text-[#71717A]" data-testid="object-queue-info">
            {hasObjects} {source === "svg" ? "imported" : ""} shapes queued
          </div>
        )}
      </div>

      <Separator className="bg-[#262626]" />

      {/* actions */}
      <div className="grid grid-cols-1 gap-2">
        <Button
          className="w-full h-10 rounded-sm bg-[#007AFF] hover:bg-[#1f8bff] text-white font-medium transition-colors duration-100 disabled:opacity-50"
          onClick={onNest}
          disabled={busy || !hasObjects}
          data-testid="btn-nest"
        >
          {busy ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Play className="h-4 w-4 mr-2" />}
          {busy ? "Nesting…" : "Run Nesting"}
        </Button>
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant="outline"
            className="h-9 rounded-sm border-[#262626] bg-[#0F0F0F] text-[#A1A1AA] hover:text-white hover:bg-[#1a1a1a] transition-colors duration-100"
            onClick={onClear}
            disabled={busy}
            data-testid="btn-clear"
          >
            <Eraser className="h-3.5 w-3.5 mr-1.5" /> Clear
          </Button>
          <Button
            variant="outline"
            className="h-9 rounded-sm border-[#262626] bg-[#0F0F0F] text-[#A1A1AA] hover:text-white hover:bg-[#1a1a1a] transition-colors duration-100"
            onClick={onReset}
            disabled={busy}
            data-testid="btn-reset"
          >
            <RotateCcw className="h-3.5 w-3.5 mr-1.5" /> Reset
          </Button>
        </div>
      </div>

      <Separator className="bg-[#262626]" />

      {/* debug */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-[11px] uppercase tracking-[0.2em] text-[#71717A] font-heading">Debug Mode</div>
          <Switch
            checked={debug.enabled}
            onCheckedChange={(v) => setDebug((d) => ({ ...d, enabled: v }))}
            className="data-[state=checked]:bg-[#007AFF]"
            data-testid="toggle-debug-mode"
          />
        </div>
        {debug.enabled && (
          <div className="rounded-sm border border-[#262626] bg-[#0F0F0F] px-3 py-1.5">
            <Toggle label="Bounding boxes" color="#FF00FF" checked={debug.showBBox} onChange={(v) => setDebug((d) => ({ ...d, showBBox: v }))} testid="toggle-bbox" />
            <Toggle label="Candidate positions" color="#007AFF" checked={debug.showCandidates} onChange={(v) => setDebug((d) => ({ ...d, showCandidates: v }))} testid="toggle-candidates" />
            <Toggle label="Rejected positions" color="#FF3B30" checked={debug.showRejected} onChange={(v) => setDebug((d) => ({ ...d, showRejected: v }))} testid="toggle-rejected" />
            <Toggle label="Collision areas" color="#FF3B30" checked={debug.showCollisions} onChange={(v) => setDebug((d) => ({ ...d, showCollisions: v }))} testid="toggle-collisions" />
            <div className="pt-1 pb-0.5 font-mono-data text-[9px] text-[#52525B] leading-relaxed">
              Debug re-runs nesting to capture candidate data. Slower on large sets.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
