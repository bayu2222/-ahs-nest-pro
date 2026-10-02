"""Bottom-Left-Fill heuristic (AHS Nesting Engine V0.1).

NOT an optimal solver. A deterministic heuristic:
  - sort shapes by area (desc), tie-broken by longest dimension then id
  - place large shapes first
  - for each shape, test the configured rotations
  - generate candidate anchor points from already-placed shapes
  - validate boundary + collision + spacing using ACTUAL polygon geometry
  - score each valid placement and keep the best (lowest layout top)

Performance: the authoritative spacing/overlap test runs against the real
polygon geometry, but each placed shape is pre-buffered by `spacing` once and
wrapped in a prepared geometry, and an STRtree provides bbox broadphase. A
candidate is invalid iff it intersects any placed buffer (buffer(spacing) turns
the "minimum distance" spacing rule into a fast intersection test).
"""

from __future__ import annotations

import time
from typing import List, Optional, Tuple

from shapely import STRtree
from shapely.affinity import translate
from shapely.geometry import Polygon, box
from shapely.prepared import prep

from ..geometry import collision
from ..geometry.transform import bbox_size, rotate_points
from .base import DebugRecord, NestingAlgorithm, NestOutcome, NestSettings, ShapeObject
from .candidates import generate_candidates
from .scoring import PlacementScorer

Point = Tuple[float, float]

_DEBUG_CAP = 600  # cap debug entries to keep payloads light


class BottomLeftFill(NestingAlgorithm):
    name = "bottom-left-fill"

    def __init__(self, scorer: Optional[PlacementScorer] = None):
        self.scorer = scorer or PlacementScorer()

    def nest(self, objects: List[ShapeObject], settings: NestSettings,
             debug: bool = False) -> NestOutcome:
        start = time.perf_counter()
        media_w = settings.media_width
        media_h = settings.effective_height()
        spacing = settings.spacing
        buf = max(spacing - collision.EPS, 0.0)
        angles = settings.rotation_angles()

        dbg = DebugRecord() if debug else None
        candidates_tested = 0
        failed = 0

        order = sorted(objects, key=lambda o: (-o.area, -o.longest_dimension, o.id))

        placed_polys: List[Polygon] = []        # true geometry (for area/output)
        placed_buffers: List[Polygon] = []       # geometry grown by spacing
        placed_prepared = []                      # prepared buffers (fast hit test)
        placed_bboxes: List[dict] = []
        tree: Optional[STRtree] = None

        for obj in order:
            rotations = []
            for angle in angles:
                rpts = rotate_points(obj.points, angle)
                rw, rh = bbox_size(rpts)
                if rw <= media_w + collision.EPS:
                    rotations.append((angle, rpts, rw, rh, Polygon(rpts)))
            if not rotations:
                obj.placed = False
                failed += 1
                continue

            anchors = generate_candidates(placed_bboxes, spacing)

            best = None
            best_top = float("inf")

            for angle, rpts, rw, rh, opoly in rotations:
                for (cx, cy) in anchors:
                    if cx < -collision.EPS or cy < -collision.EPS:
                        continue
                    if cx + rw > media_w + collision.EPS:
                        continue
                    top = cy + rh
                    if top - best_top > collision.EPS:
                        break  # anchors sorted bottom-up; cannot beat best
                    if top > media_h + collision.EPS:
                        continue

                    candidates_tested += 1

                    # Broadphase first: only build real geometry when a placed
                    # buffer's bbox overlaps this candidate's bbox.
                    hit = None
                    if tree is not None and placed_buffers:
                        q = box(cx, cy, cx + rw, cy + rh)
                        idxs = tree.query(q)
                        if len(idxs):
                            poly = translate(opoly, xoff=cx, yoff=cy)
                            for i in idxs:
                                if placed_prepared[i].intersects(poly):
                                    hit = int(i)
                                    break

                    if hit is not None:
                        if dbg and len(dbg.rejected) < _DEBUG_CAP:
                            dbg.rejected.append(
                                {"x": cx, "y": cy, "width": rw, "height": rh,
                                 "reason": "collision"})
                            inter = translate(opoly, xoff=cx, yoff=cy).intersection(
                                placed_buffers[hit])
                            if (not inter.is_empty
                                    and len(dbg.collisions) < _DEBUG_CAP):
                                dbg.collisions.append(self._poly_debug(inter))
                        continue

                    if dbg and len(dbg.candidates) < _DEBUG_CAP:
                        dbg.candidates.append(
                            {"x": cx, "y": cy, "width": rw, "height": rh})

                    score = self.scorer.score(cx, cy, rw, rh)
                    if best is None or score < best[0] - collision.EPS:
                        best = (score, angle, rpts, rw, rh, cx, cy)
                        best_top = top

            if best is None:
                obj.placed = False
                failed += 1
                continue

            _, angle, rpts, rw, rh, px, py = best
            poly = translate(Polygon(rpts), xoff=px, yoff=py)
            placed_pts = [(round(px + x, 6), round(py + y, 6)) for x, y in rpts]
            obj.placed = True
            obj.x = round(px, 6)
            obj.y = round(py, 6)
            obj.rotation = round(angle, 6)
            obj.rotated_points = placed_pts
            obj.bbox = {
                "minX": round(px, 6), "minY": round(py, 6),
                "maxX": round(px + rw, 6), "maxY": round(py + rh, 6),
            }
            placed_polys.append(poly)
            pbuf = poly.buffer(buf) if buf > 0 else poly
            placed_buffers.append(pbuf)
            placed_prepared.append(prep(pbuf))
            placed_bboxes.append(obj.bbox)
            tree = STRtree(placed_buffers)
            if dbg:
                dbg.bounding_boxes.append({"id": obj.id, **obj.bbox})

        used_width = max((b["maxX"] for b in placed_bboxes), default=0.0)
        used_height = max((b["maxY"] for b in placed_bboxes), default=0.0)
        placed_count = sum(1 for o in objects if o.placed)
        used_area = sum(Polygon(o.rotated_points).area for o in objects if o.placed)
        denom = media_w * used_height
        utilization = (used_area / denom * 100.0) if denom > 0 else 0.0
        final_media_h = media_h if media_h != float("inf") else used_height

        return NestOutcome(
            objects=objects,
            media_width=round(media_w, 6),
            media_height=round(final_media_h, 6),
            used_width=round(used_width, 6),
            used_height=round(used_height, 6),
            utilization=round(utilization, 4),
            processing_time=round(time.perf_counter() - start, 6),
            object_count=len(objects),
            placed_count=placed_count,
            failed_placements=failed,
            candidates_tested=candidates_tested,
            debug=dbg,
        )

    @staticmethod
    def _poly_debug(geom) -> dict:
        try:
            if geom.geom_type == "Polygon":
                coords = [[round(x, 4), round(y, 4)] for x, y in geom.exterior.coords]
            else:
                hull = geom.convex_hull
                coords = [[round(x, 4), round(y, 4)] for x, y in hull.exterior.coords]
        except Exception:
            coords = []
        return {"points": coords}
