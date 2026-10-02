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
- P1: Performance — STRtree rebuilt per placement (O(n²)); 100 objects @ step 5° ≈ 25s. Incremental index / coarser candidate pruning for V0.2.
- P2: No-Fit-Polygon (NFP) candidate generation for tighter packing.
- P2: Local optimization / simulated annealing / genetic strategies via Optimizer ABC.
- P2: SVG path import from CorelDRAW (input layer already isolated).
- P3: Remove unused MongoDB scaffolding.

## Notes
V0.1 is an explicitly heuristic prototype — NOT an optimal nesting solution. Priorities honored: correctness, deterministic behavior, collision safety, easy debugging, modular architecture.
