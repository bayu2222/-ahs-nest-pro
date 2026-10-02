import React, { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Box, Boxes } from "lucide-react";
import { api } from "@/lib/api";
import { importErrorMessage, readFileText, toNestPayload, validateSvgFile } from "@/lib/svgImport";
import ControlPanel from "@/components/ControlPanel";
import StatsPanel from "@/components/StatsPanel";
import SpacingVerification from "@/components/SpacingVerification";
import BenchmarkPanel from "@/components/BenchmarkPanel";
import NestCanvas from "@/components/NestCanvas";

const DEFAULT_SETTINGS = {
  mediaWidth: 120,
  mediaHeight: 100,
  heightMode: "auto",
  spacing: 0.3,
  rotationStep: 5,
  allowRotation: true,
};

const DEFAULT_DEBUG = {
  enabled: false,
  showBBox: true,
  showCandidates: false,
  showRejected: false,
  showCollisions: true,
};

const DEFAULT_SVG_IMPORT = { status: "idle", fileName: null, data: null, error: null };

function toPayload(settings) {
  return {
    media_width: settings.mediaWidth,
    media_height: settings.mediaHeight,
    height_mode: settings.heightMode,
    spacing: settings.spacing,
    rotation_step: settings.rotationStep,
    allow_rotation: settings.allowRotation,
    max_angle: 360,
    algorithm: "bottom-left-fill",
  };
}

export default function NestingStudio() {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [count, setCount] = useState(20);
  const [objects, setObjects] = useState([]);
  const [result, setResult] = useState(null);
  const [debug, setDebug] = useState(DEFAULT_DEBUG);
  const [busy, setBusy] = useState(false);
  const [benchBusy, setBenchBusy] = useState(false);
  const [benchResults, setBenchResults] = useState(null);
  const seedRef = useRef(42);

  // Phase C: object source. `objects` keeps the random test set (unchanged
  // behaviour); imported SVG geometry lives in svgImport.data.objects. The
  // active queue feeds the SAME nesting pipeline either way.
  const [source, setSource] = useState("random"); // "random" | "svg"
  const [svgImport, setSvgImport] = useState(DEFAULT_SVG_IMPORT);
  const svgObjects = svgImport.data?.objects || [];
  const activeObjects = source === "svg" ? svgObjects : objects;

  const handleSourceChange = (next) => {
    if (next === source) return;
    setSource(next);
    setResult(null);
  };

  const handleImportSvg = async (file) => {
    const check = validateSvgFile(file);
    if (!check.ok) {
      setSvgImport({ status: "error", fileName: file?.name || null, data: null, error: check.error });
      setResult(null);
      toast.error("Invalid file", { description: check.error });
      return;
    }
    try {
      setSvgImport({ status: "loading", fileName: file.name, data: null, error: null });
      setResult(null);
      const text = await readFileText(file);
      const data = await api.importSvg(text, file.name);
      setSvgImport({ status: "success", fileName: file.name, data, error: null });
      setSource("svg");
      toast.success(`Imported ${data.importedCount} object${data.importedCount === 1 ? "" : "s"}`, {
        description: data.failedCount ? `${data.failedCount} element(s) skipped · ${file.name}` : file.name,
      });
    } catch (e) {
      const msg = importErrorMessage(e);
      setSvgImport({ status: "error", fileName: file.name, data: null, error: msg });
      toast.error("SVG import failed", { description: msg });
    }
  };

  const handleGenerate = async () => {
    try {
      setBusy(true);
      const seed = Math.floor(Math.random() * 100000);
      seedRef.current = seed;
      const objs = await api.generate(count, seed, null);
      setObjects(objs);
      setResult(null);
      toast.success(`Generated ${objs.length} test shapes`, { description: `seed ${seed}` });
    } catch (e) {
      toast.error("Failed to generate objects", { description: String(e?.message || e) });
    } finally {
      setBusy(false);
    }
  };

  const runNest = async (useDebug) => {
    if (!activeObjects.length) return;
    const payload = toNestPayload(activeObjects);
    const data = await api.nest(payload, toPayload(settings), useDebug);
    setResult(data);
    return data;
  };

  const handleNest = async () => {
    try {
      setBusy(true);
      const data = await runNest(debug.enabled);
      const s = data.stats;
      if (s.failedPlacements > 0) {
        toast.warning(`${s.placedCount}/${s.objectCount} placed`, {
          description: `${s.failedPlacements} did not fit · ${(s.processingTime * 1000).toFixed(0)}ms`,
        });
      } else {
        toast.success(`Nested ${s.placedCount} objects`, {
          description: `${s.utilization.toFixed(1)}% util · ${(s.processingTime * 1000).toFixed(0)}ms`,
        });
      }
    } catch (e) {
      toast.error("Nesting failed", { description: String(e?.message || e) });
    } finally {
      setBusy(false);
    }
  };

  // Re-run with debug data when debug mode is switched on and a layout exists.
  const prevDebug = useRef(false);
  useEffect(() => {
    if (debug.enabled && !prevDebug.current && activeObjects.length && result) {
      runNest(true).catch(() => {});
    }
    prevDebug.current = debug.enabled;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debug.enabled]);

  const handleClear = () => {
    if (source === "svg") {
      setSvgImport(DEFAULT_SVG_IMPORT);
    } else {
      setObjects([]);
    }
    setResult(null);
    toast("Canvas cleared");
  };

  const handleReset = () => {
    setSettings(DEFAULT_SETTINGS);
    setCount(20);
    setObjects([]);
    setResult(null);
    setBenchResults(null);
    setDebug(DEFAULT_DEBUG);
    setSource("random");
    setSvgImport(DEFAULT_SVG_IMPORT);
    toast("Reset to defaults");
  };

  const handleBenchmark = async (counts) => {
    try {
      setBenchBusy(true);
      toast("Running benchmark…", { description: `${counts.join(", ")} objects` });
      const res = await api.benchmark(counts, toPayload(settings), seedRef.current);
      setBenchResults(res);
      toast.success("Benchmark complete");
    } catch (e) {
      toast.error("Benchmark failed", { description: String(e?.message || e) });
    } finally {
      setBenchBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white">
      {/* header */}
      <header className="border-b border-[#262626] px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-sm bg-[#007AFF] flex items-center justify-center">
            <Boxes className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="font-heading text-base font-semibold tracking-tight leading-none">
              AHS Nesting Engine
            </h1>
            <p className="text-[11px] text-[#71717A] mt-0.5 font-mono-data">
              Irregular-shape nesting · heuristic prototype
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono-data text-[10px] uppercase tracking-[0.2em] text-[#EAB308] border border-[#EAB308]/40 px-2 py-1 rounded-sm">
            V0.1 · Not Optimal
          </span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 p-4">
        {/* left: controls / benchmark */}
        <aside className="lg:col-span-3">
          <div className="border border-[#262626] bg-[#141414] rounded-sm">
            <Tabs defaultValue="controls" className="w-full">
              <TabsList className="w-full grid grid-cols-2 bg-[#0F0F0F] rounded-none rounded-t-sm h-10 p-0 border-b border-[#262626]">
                <TabsTrigger
                  value="controls"
                  className="rounded-none h-full text-xs uppercase tracking-wider data-[state=active]:bg-[#141414] data-[state=active]:text-white text-[#71717A] data-[state=active]:shadow-none"
                  data-testid="tab-controls"
                >
                  <Box className="h-3.5 w-3.5 mr-1.5" /> Controls
                </TabsTrigger>
                <TabsTrigger
                  value="benchmark"
                  className="rounded-none h-full text-xs uppercase tracking-wider data-[state=active]:bg-[#141414] data-[state=active]:text-white text-[#71717A] data-[state=active]:shadow-none"
                  data-testid="tab-benchmark"
                >
                  <Boxes className="h-3.5 w-3.5 mr-1.5" /> Bench
                </TabsTrigger>
              </TabsList>
              <TabsContent value="controls" className="p-4 mt-0">
                <ControlPanel
                  settings={settings}
                  setSettings={setSettings}
                  count={count}
                  setCount={setCount}
                  onGenerate={handleGenerate}
                  onNest={handleNest}
                  onClear={handleClear}
                  onReset={handleReset}
                  busy={busy}
                  hasObjects={activeObjects.length}
                  debug={debug}
                  setDebug={setDebug}
                  source={source}
                  setSource={handleSourceChange}
                  svgImport={svgImport}
                  onImportSvg={handleImportSvg}
                />
              </TabsContent>
              <TabsContent value="benchmark" className="p-4 mt-0">
                <BenchmarkPanel
                  onRun={handleBenchmark}
                  results={benchResults}
                  busy={benchBusy}
                  settings={settings}
                />
              </TabsContent>
            </Tabs>
          </div>
        </aside>

        {/* center: canvas */}
        <main className="lg:col-span-6">
          <div className="border border-[#262626] bg-[#141414] rounded-sm p-4 h-full">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[11px] uppercase tracking-[0.2em] text-[#71717A] font-heading">
                Media Viewport
              </div>
              <div className="font-mono-data text-[11px] text-[#A1A1AA]">
                {settings.heightMode === "auto" ? "AUTO-HEIGHT" : "FIXED-HEIGHT"} ·{" "}
                {settings.mediaWidth}cm wide
              </div>
            </div>
            <NestCanvas
              result={result}
              settings={settings}
              debug={debug}
              preview={
                source === "svg" && !result && svgImport.status === "success" && svgObjects.length
                  ? { objects: svgObjects, document: svgImport.data?.document, fileName: svgImport.fileName }
                  : null
              }
              emptyHint={
                source === "svg"
                  ? svgObjects.length
                    ? `${svgObjects.length} imported shapes previewed at their SVG positions — press "Run Nesting"`
                    : svgImport.status === "error"
                      ? "SVG import failed — fix the file and import again."
                      : 'No SVG imported. Press "Import SVG" to load geometry.'
                  : objects.length
                    ? `${objects.length} shapes queued — press "Run Nesting"`
                    : 'No objects. Press "Generate Objects" to create a test set.'
              }
            />
          </div>
        </main>

        {/* right: stats */}
        <aside className="lg:col-span-3 space-y-4">
          <div className="border border-[#262626] bg-[#141414] rounded-sm p-4">
            <div className="text-[11px] uppercase tracking-[0.2em] text-[#71717A] font-heading mb-3">
              Result Metrics
            </div>
            <StatsPanel stats={result?.stats} />
          </div>
          <SpacingVerification verification={result?.verification} />
          <div className="border border-[#262626] bg-[#141414] rounded-sm p-4">
            <div className="text-[11px] uppercase tracking-[0.2em] text-[#71717A] font-heading mb-2">
              Notes
            </div>
            <p className="text-[11px] leading-relaxed text-[#71717A]">
              V0.1 uses a deterministic Bottom-Left-Fill heuristic with exact polygon
              collision (Shapely). Spacing is a true geometric gap, not bbox padding.
              Results are reproducible for identical input & settings. This is a prototype,
              not an optimal nesting solution.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
