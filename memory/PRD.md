# AHS Nesting Engine — PRD

## Original Problem Statement
Build V0.1 of a standalone irregular-shape nesting engine (future core of the commercial CorelDRAW tool "AHS Nest Pro"). Scope is ONLY the nesting algorithm prototype + a visual tester. No CorelDRAW plugin, licensing, subscription, login, installer, or payments.

## Architecture
- **Backend (FastAPI + Shapely)** — modular, UI-independent engine. Internal unit = centimeters, float precision preserved.
  - `engine/geometry/` — `shapes.py` (rectangle/circle/triangle/polygon → canonical point lists), `transform.py` (rotation about center, bbox), `collision.py` (within-media, spacing/overlap via real polygon distance).
  - `engine/nesting/` — `base.py` (NestSettings, ShapeObject, NestOutcome, NestingAlgorithm ABC), `candidates.py` (corner-point candidate generator), `scoring.py` (modular PlacementScorer), `heuristic.py` (deterministic Bottom-Left-Fill with STRtree broadphase + prepared buffered geometry), `registry.py` (pluggable algorithms).
  - `engine/optimization/` — Optimizer ABC placeholder (future NFP / simulated annealing / genetic).
  - `engine/benchmark/` — benchmark runner.
  - `engine/test_data/` — seeded deterministic random shape generator.
  - `server.py` — `/api/algorithms`, `/api/generate`, `/api/nest`, `/api/benchmark`.
- **Frontend (React + SVG)** — dark technical "command-center" UI. `NestingStudio` (state/handlers), `ControlPanel`, `StatsPanel`, `BenchmarkPanel`, `NestCanvas` (SVG, cm ruler, debug overlays), `lib/api.js`, `lib/colors.js`.

## Core Requirements (static)
- Fixed media width default 120cm (editable); auto OR fixed media height.
- Spacing as a true geometric gap (default 0.3cm); rotation 0–360° with configurable step (default 5°).
- Prevent overlap, keep inside media, exact polygon collision (not bbox-only), minimize used height.
- Deterministic for identical input+settings. Modular so NFP/optimizers can be added.
- Output per object {id,x,y,rotation,width,height} + summary {mediaWidth,usedHeight,utilization,processingTime,objectCount}.

## Implemented (2026-06)
- Full geometry/collision/spacing layer with Shapely; rotation about center.
- Bottom-Left-Fill heuristic: sort by area desc, corner-point candidates, exact spacing/boundary validation, modular scoring, STRtree broadphase. Verified: 0 overlaps, 0 out-of-bounds, deterministic.
- Shape types: rectangle, circle, triangle, arbitrary polygon (SVG-path-ready input layer).
- Visual tester: SVG media viewport with cm ruler (auto-fit), nested polygons with IDs + rotation labels, live metrics (utilization, used W/H, counts, candidates, processing time).
- Controls: generate random objects, nest, clear, reset, spacing, rotation step, media width/height, auto/fixed height, allow-rotation.
- Benchmark mode (10/20/50/100) with results table (time, height, util%, failures, candidates).
- Debug mode overlays: bounding boxes, candidate positions, rejected positions, collision areas.
- Tested end-to-end (testing agent): backend 100%, frontend 100%.

## Known Characteristics / Backlog (future versions)
- P1: Performance — candidate pruning / incremental index (O(n²) per placement); 100 objects @ step 5° ≈ 15s (numpy bbox broadphase + prepared geometry; STRtree no longer used).
- P2: No-Fit-Polygon (NFP) candidate generation for tighter packing.
- P2: Local optimization / simulated annealing / genetic strategies via Optimizer ABC.
- P2: Layout / SVG export of the nested result (same cm, bottom-left convention).
- P3: Remove unused MongoDB scaffolding.

## SVG Import Phase C (frontend UI) — implemented
- `ControlPanel`: "Objects → Source" segmented control **Random Test | Imported SVG** (`btn-source-random` / `btn-source-svg`). Random generation unchanged.
- `SvgImportPanel.jsx`: hidden `<input type=file accept=".svg,image/svg+xml">` + "Import SVG" button; states idle / loading / success (file name, imported count, skipped count + failures, document size/unit) / error (clear message from backend `detail.error`).
- `lib/svgImport.js` (pure, Jest-tested 13/13): `validateSvgFile`, `readFileText`, `importErrorMessage`, `toNestPayload`, `previewExtent`, `ringsToPathD`. No unit conversion in the frontend.
- `NestingStudio`: `source` + `svgImport` state; `activeObjects = source==='svg' ? imported : random` feeds the SAME `/api/nest` pipeline via `toNestPayload` (`{id,type:'polygon',width,height,points}`); Clear/Reset aware of source.
- `NestCanvas`: `preview` prop renders imported geometry at its backend cm coordinates (evenodd path → holes visible) with "PREVIEW · n imported · not nested" label; widens the view if the document is wider than the media. Existing metrics / spacing verification / debug overlays reused as-is after nesting.

## SVG Import Phase B (backend only) — implemented
- `engine/svg_import/importer.py` (svgelements + Shapely): elements path/rect/circle/ellipse/polygon/polyline; transforms translate/rotate/scale/matrix/skew (reified); curves flattened with `CURVE_MAX_CHORD_CM=0.05` (8–128 samples/segment).
- Units: svgelements resolves to px at `dpi`; px→cm = 2.54/dpi (dpi per request, default 96). Physical root units (mm/cm/in/pt/pc) are exact and DPI-independent (factor calibrated from declared width). viewBox mapped onto viewport; viewBox-only → user unit = px@dpi; no size/no viewBox → content extent.
- Convention: output cm, origin bottom-left, +Y up. Y flipped exactly once in the importer (`y_ahs = documentHeightCm − y_svg`); exterior CCW / holes CW. Engine untouched.
- Compound paths: even-odd depth classification → holes kept as `holes` (interior rings), never separate objects; one object per SVG element (disjoint outers → largest kept + warning). Output always a valid Shapely polygon; `points` (exterior) feeds `/api/nest` as `type:'polygon'`.
- API: `POST /api/import-svg {svg, filename?, dpi?}` → 200 `{objects[{id,index,svgType,type,points,holes,width,height,bbox,area,warnings}], importedCount, failedCount, failures, document, coordinateSystem, supported, error, filename}`; 400 `{detail:{error,failures,filename}}` on unparseable/no-geometry; 422 on invalid body. `GET /api/import-svg/capabilities`.
- Tests: `backend/tests/test_svg_import.py` (37) + `conftest.py`; full suite 54/54.

## Notes
V0.1 is an explicitly heuristic prototype — NOT an optimal nesting solution. Priorities honored: correctness, deterministic behavior, collision safety, easy debugging, modular architecture.
