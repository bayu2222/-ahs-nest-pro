// Pure helpers for the SVG Import UI (Phase C). No React, no unit conversion:
// the backend (/api/import-svg) already normalizes geometry to cm, origin
// bottom-left, +Y up. The frontend only validates the file, reads its text,
// forwards it, and maps backend objects into the existing /api/nest payload.

export const SVG_ACCEPT = ".svg,image/svg+xml";
export const MAX_SVG_BYTES = 20 * 1024 * 1024; // mirrors backend max_length guard

export function validateSvgFile(file) {
  if (!file) return { ok: false, error: "No file selected." };
  const name = String(file.name || "");
  const isSvgName = /\.svg$/i.test(name);
  const isSvgType = (file.type || "").toLowerCase() === "image/svg+xml";
  if (!isSvgName && !isSvgType) {
    return { ok: false, error: `"${name || "file"}" is not an SVG. Only .svg files are supported.` };
  }
  if (typeof file.size === "number" && file.size > MAX_SVG_BYTES) {
    return { ok: false, error: `"${name}" is too large (max ${MAX_SVG_BYTES / 1024 / 1024} MB).` };
  }
  if (typeof file.size === "number" && file.size === 0) {
    return { ok: false, error: `"${name}" is empty.` };
  }
  return { ok: true, error: null };
}

export function readFileText(file) {
  if (file && typeof file.text === "function") return file.text();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Could not read the selected file."));
    reader.readAsText(file);
  });
}

// Turn an axios/network error from POST /api/import-svg into one clear message.
export function importErrorMessage(err) {
  const detail = err?.response?.data?.detail;
  if (detail) {
    if (typeof detail === "string") return detail;
    if (detail.error) {
      const n = Array.isArray(detail.failures) ? detail.failures.length : 0;
      const first = n ? detail.failures[0] : null;
      const hint = first ? ` (${n} element${n > 1 ? "s" : ""} rejected, e.g. <${first.element}>: ${first.reason})` : "";
      return `${detail.error}${hint}`;
    }
    if (Array.isArray(detail) && detail[0]?.msg) return `Invalid request: ${detail[0].msg}`;
  }
  if (err?.code === "ECONNABORTED") return "Import timed out. Try a smaller SVG.";
  if (err?.message === "Network Error") return "Cannot reach the backend. Check your connection.";
  return err?.message ? `Import failed: ${err.message}` : "Import failed.";
}

// Backend import objects -> exact same payload shape /api/nest already accepts.
export function toNestPayload(objects) {
  return (objects || []).map((o) => ({
    id: o.id,
    type: o.type,
    width: o.width,
    height: o.height,
    points: o.points,
  }));
}

// Extent (cm) used by the canvas to frame imported geometry before nesting.
export function previewExtent(objects, document) {
  let maxX = 0;
  let maxY = 0;
  for (const o of objects || []) {
    if (o?.bbox) {
      maxX = Math.max(maxX, o.bbox.maxX);
      maxY = Math.max(maxY, o.bbox.maxY);
    }
  }
  return {
    widthCm: Math.max(document?.widthCm || 0, maxX),
    heightCm: Math.max(document?.heightCm || 0, maxY),
  };
}

// SVG path data (even-odd) for exterior + holes, via a caller-supplied projector.
export function ringsToPathD(points, holes, X, Y) {
  const ring = (pts) => (pts && pts.length ? `M ${pts.map(([x, y]) => `${X(x)} ${Y(y)}`).join(" L ")} Z` : "");
  return [ring(points), ...(holes || []).map(ring)].filter(Boolean).join(" ");
}
