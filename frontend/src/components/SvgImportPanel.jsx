import React, { useRef } from "react";
import { Button } from "@/components/ui/button";
import { FileUp, Loader2, CheckCircle2, XCircle, FileCode2 } from "lucide-react";
import { SVG_ACCEPT } from "@/lib/svgImport";

/**
 * SVG Import panel (Phase C). Pure presentation + file picker; validation,
 * reading and the API call live in NestingStudio (handleImportSvg).
 *
 * svgImport = { status: "idle" | "loading" | "success" | "error",
 *               fileName, data (backend response), error }
 */
export default function SvgImportPanel({ svgImport, onImportSvg, disabled }) {
  const inputRef = useRef(null);
  const { status, fileName, data, error } = svgImport;
  const loading = status === "loading";

  const pick = () => {
    if (loading || disabled) return;
    inputRef.current?.click();
  };

  const onChange = (e) => {
    const file = e.target.files && e.target.files[0];
    // reset so picking the same file again re-triggers change
    e.target.value = "";
    if (file) onImportSvg(file);
  };

  const doc = data?.document;

  return (
    <div className="space-y-2.5" data-testid="svg-import-panel">
      <input
        ref={inputRef}
        type="file"
        accept={SVG_ACCEPT}
        className="hidden"
        onChange={onChange}
        data-testid="input-svg-file"
      />
      <Button
        variant="outline"
        className="w-full h-9 rounded-sm border-[#262626] bg-[#0F0F0F] text-[#E4E4E7] hover:bg-[#1a1a1a] hover:text-white transition-colors duration-100"
        onClick={pick}
        disabled={loading || disabled}
        data-testid="btn-import-svg"
      >
        {loading ? <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" /> : <FileUp className="h-3.5 w-3.5 mr-2" />}
        {loading ? "Importing…" : status === "success" ? "Import another SVG" : "Import SVG"}
      </Button>

      {/* idle */}
      {status === "idle" && (
        <p className="text-[11px] leading-relaxed text-[#71717A] font-mono-data" data-testid="svg-import-empty">
          No SVG imported. Choose a <span className="text-[#A1A1AA]">.svg</span> file (e.g. exported from
          CorelDRAW). Geometry is converted to cm by the backend.
        </p>
      )}

      {/* loading */}
      {status === "loading" && (
        <p className="text-[11px] text-[#A1A1AA] font-mono-data truncate" data-testid="svg-import-loading">
          Importing <span className="text-white">{fileName}</span>…
        </p>
      )}

      {/* success */}
      {status === "success" && data && (
        <div className="rounded-sm border border-[#22C55E]/40 bg-[#22C55E]/[0.06] px-3 py-2 space-y-1.5" data-testid="svg-import-success">
          <div className="flex items-center gap-1.5 text-[11px] text-[#22C55E] font-mono-data min-w-0">
            <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate" title={fileName} data-testid="svg-import-filename">{fileName}</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="font-mono-data text-lg font-semibold leading-none text-white" data-testid="svg-import-count">
              {data.importedCount}
            </span>
            <span className="font-mono-data text-[11px] text-[#71717A]">
              object{data.importedCount === 1 ? "" : "s"} imported
            </span>
            {data.failedCount > 0 && (
              <span className="ml-auto font-mono-data text-[10px] text-[#EAB308]" data-testid="svg-import-failed">
                {data.failedCount} skipped
              </span>
            )}
          </div>
          {doc && (
            <div className="font-mono-data text-[10px] text-[#71717A] leading-relaxed" data-testid="svg-import-docinfo">
              {doc.widthCm != null && doc.heightCm != null
                ? `${Number(doc.widthCm).toFixed(2)} × ${Number(doc.heightCm).toFixed(2)} cm`
                : "size n/a"}
              {" · "}
              {doc.sourceUnit ? `unit ${doc.sourceUnit}` : doc.unitBasis}
              {doc.unitBasis !== "physical" ? ` · ${doc.dpi} dpi` : ""}
            </div>
          )}
          {data.failedCount > 0 && Array.isArray(data.failures) && (
            <ul className="font-mono-data text-[10px] text-[#A1A1AA] leading-relaxed list-disc pl-4" data-testid="svg-import-failures">
              {data.failures.slice(0, 3).map((f, i) => (
                <li key={i}>
                  &lt;{f.element}&gt;{f.id ? ` #${f.id}` : ""}: {f.reason}
                </li>
              ))}
              {data.failures.length > 3 && <li>+{data.failures.length - 3} more</li>}
            </ul>
          )}
        </div>
      )}

      {/* error */}
      {status === "error" && (
        <div className="rounded-sm border border-[#FF3B30]/50 bg-[#FF3B30]/[0.08] px-3 py-2 space-y-1" data-testid="svg-import-error">
          <div className="flex items-center gap-1.5 text-[11px] text-[#FF3B30] font-mono-data min-w-0">
            <XCircle className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate" title={fileName}>{fileName || "Import failed"}</span>
          </div>
          <p className="text-[11px] leading-relaxed text-[#FCA5A5] break-words" data-testid="svg-import-error-message">
            {error}
          </p>
        </div>
      )}

      <div className="flex items-start gap-1.5 pt-0.5 font-mono-data text-[9px] text-[#52525B] leading-relaxed">
        <FileCode2 className="h-3 w-3 mt-[1px] shrink-0" />
        <span>path · rect · circle · ellipse · polygon · polyline · transforms. Holes stay holes.</span>
      </div>
    </div>
  );
}
