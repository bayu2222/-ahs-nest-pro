/* eslint-env jest */
import {
  importErrorMessage,
  previewExtent,
  readFileText,
  ringsToPathD,
  toNestPayload,
  validateSvgFile,
} from "./svgImport";

describe("validateSvgFile", () => {
  it("accepts .svg by extension", () => {
    expect(validateSvgFile(new File(["<svg/>"], "part.svg", { type: "" })).ok).toBe(true);
  });
  it("accepts image/svg+xml mime even with odd name", () => {
    expect(validateSvgFile(new File(["<svg/>"], "export", { type: "image/svg+xml" })).ok).toBe(true);
  });
  it("rejects non-svg files with a clear message", () => {
    const r = validateSvgFile(new File(["x"], "photo.png", { type: "image/png" }));
    expect(r.ok).toBe(false);
    expect(r.error).toMatch(/not an SVG/);
    expect(r.error).toMatch(/photo\.png/);
  });
  it("rejects empty and missing files", () => {
    expect(validateSvgFile(new File([], "empty.svg")).error).toMatch(/empty/);
    expect(validateSvgFile(null).ok).toBe(false);
  });
});

describe("readFileText", () => {
  it("reads file contents as text", async () => {
    const text = await readFileText(new File(['<svg xmlns="http://www.w3.org/2000/svg"/>'], "a.svg"));
    expect(text).toContain("<svg");
  });
});

describe("importErrorMessage", () => {
  it("uses backend detail.error and summarizes failures", () => {
    const err = {
      response: {
        status: 400,
        data: {
          detail: {
            error: "No supported/valid geometry found in the SVG.",
            failures: [{ element: "line", id: null, reason: "no usable closed geometry" }],
          },
        },
      },
    };
    const msg = importErrorMessage(err);
    expect(msg).toMatch(/No supported\/valid geometry/);
    expect(msg).toMatch(/<line>/);
  });
  it("handles parse errors from backend", () => {
    const err = { response: { data: { detail: { error: "Could not parse SVG: bad token", failures: [] } } } };
    expect(importErrorMessage(err)).toBe("Could not parse SVG: bad token");
  });
  it("handles FastAPI 422 validation lists", () => {
    const err = { response: { data: { detail: [{ msg: "Field required", loc: ["body", "svg"] }] } } };
    expect(importErrorMessage(err)).toMatch(/Invalid request: Field required/);
  });
  it("handles network errors", () => {
    expect(importErrorMessage({ message: "Network Error" })).toMatch(/Cannot reach the backend/);
    expect(importErrorMessage({ code: "ECONNABORTED" })).toMatch(/timed out/);
    expect(importErrorMessage(new Error("boom"))).toBe("Import failed: boom");
  });
});

describe("toNestPayload", () => {
  it("maps imported objects to the existing /api/nest shape without unit conversion", () => {
    const imported = [
      {
        id: "frame", index: 1, svgType: "path", type: "polygon",
        points: [[4, 2], [6, 2], [6, 4], [4, 4]], holes: [[[4.5, 2.5], [5.5, 2.5], [5.5, 3.5], [4.5, 3.5]]],
        width: 2, height: 2, bbox: { minX: 4, minY: 2, maxX: 6, maxY: 4 }, area: 3, warnings: [],
      },
    ];
    expect(toNestPayload(imported)).toEqual([
      { id: "frame", type: "polygon", width: 2, height: 2, points: [[4, 2], [6, 2], [6, 4], [4, 4]] },
    ]);
  });
  it("tolerates empty input", () => {
    expect(toNestPayload(undefined)).toEqual([]);
  });
});

describe("previewExtent", () => {
  it("frames the larger of document size and content bbox", () => {
    const objs = [{ bbox: { minX: 0, minY: 0, maxX: 12, maxY: 3 } }];
    expect(previewExtent(objs, { widthCm: 10, heightCm: 5 })).toEqual({ widthCm: 12, heightCm: 5 });
    expect(previewExtent(objs, null)).toEqual({ widthCm: 12, heightCm: 3 });
  });
});

describe("ringsToPathD", () => {
  it("emits exterior then holes as closed sub-paths", () => {
    const X = (x) => x * 10;
    const Y = (y) => 100 - y * 10;
    const d = ringsToPathD([[0, 0], [1, 0], [1, 1]], [[[0.2, 0.2], [0.4, 0.2], [0.4, 0.4]]], X, Y);
    expect(d).toBe("M 0 100 L 10 100 L 10 90 Z M 2 98 L 4 98 L 4 96 Z");
  });
});
