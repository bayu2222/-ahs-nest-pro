"""SVG -> normalized cm polygons (Phase A).

Supported elements: path, rect, circle, ellipse, polygon, polyline.
Supported transforms: translate, rotate, scale (and any affine matrix that
svgelements resolves, e.g. matrix/skew) — svgelements bakes the full transform
chain + viewBox into absolute coordinates, so transforms are never ignored.

Unit strategy (deterministic):
  svgelements resolves the document to CSS pixels at a fixed 96 ppi. Physical
  units (mm, cm, in, pt) on the root width/height are therefore honored exactly.
  If the file only has a viewBox and no physical width/height, user units are
  treated as pixels at 96 ppi (documented fallback). Final px -> cm uses
  1 in = 2.54 cm, 96 px = 1 in  ->  CM_PER_PX = 2.54 / 96.
"""

import io
import re
from typing import List

from shapely.geometry import Polygon
from svgelements import Arc, Close, CubicBezier, Line, Move, Path
from svgelements import Polygon as SvgPolygon
from svgelements import QuadraticBezier, Shape, SVG

PPI = 96.0
CM_PER_PX = 2.54 / PPI
CURVE_STEPS = 24  # samples per curved segment when flattening

SUPPORTED_ELEMENTS = ["path", "rect", "circle", "ellipse", "polygon", "polyline"]
SUPPORTED_TRANSFORMS = ["translate", "rotate", "scale", "matrix", "skewX", "skewY"]

_ROOT_SIZE_RE = re.compile(
    r"<svg\b[^>]*?\b(width|height)\s*=\s*\"?([0-9.]+)\s*(mm|cm|in|pt|pc|px)?",
    re.IGNORECASE | re.DOTALL,
)


def _flatten(path: Path) -> List[list]:
    """Flatten a (reified/absolute) Path into one or more rings of (x, y) px."""
    rings: List[list] = []
    cur: list = []
    for seg in path:
        if isinstance(seg, Move):
            if len(cur) >= 3:
                rings.append(cur)
            cur = []
            if seg.end is not None:
                cur.append((seg.end.x, seg.end.y))
        elif isinstance(seg, (Line, Close)):
            if seg.end is not None:
                cur.append((seg.end.x, seg.end.y))
        elif isinstance(seg, (CubicBezier, QuadraticBezier, Arc)):
            for i in range(1, CURVE_STEPS + 1):
                p = seg.point(i / CURVE_STEPS)
                cur.append((p.x, p.y))
        else:
            if getattr(seg, "end", None) is not None:
                cur.append((seg.end.x, seg.end.y))
    if len(cur) >= 3:
        rings.append(cur)
    return rings


def _largest_ring_cm(rings: List[list]):
    """Pick the largest-area ring, convert px->cm, sanitize with Shapely.

    Returns (points_cm, area_cm2) or None if nothing usable.
    """
    best = None
    best_area = -1.0
    for ring in rings:
        pts = [(x * CM_PER_PX, y * CM_PER_PX) for (x, y) in ring]
        try:
            poly = Polygon(pts)
            if not poly.is_valid:
                poly = poly.buffer(0)
            if poly.is_empty:
                continue
            if poly.geom_type == "MultiPolygon":
                poly = max(poly.geoms, key=lambda g: g.area)
            area = poly.area
            if area > best_area:
                best = list(poly.exterior.coords)[:-1]  # drop closing dup
                best_area = area
        except Exception:
            continue
    if best is None or best_area <= 1e-9:
        return None
    return [[round(x, 6), round(y, 6)] for (x, y) in best], best_area


def _detect_unit_basis(svg_text: str) -> str:
    for _, _, unit in _ROOT_SIZE_RE.findall(svg_text):
        if unit and unit.lower() in ("mm", "cm", "in", "pt", "pc"):
            return "physical"
    return "viewbox-fallback"


def import_svg(svg_text: str) -> dict:
    """Parse SVG text into normalized cm polygon objects.

    Returns a dict:
      {
        objects: [{id, type:'polygon', svgType, index, points, width, height,
                   x0, y0}],
        importedCount, failedCount,
        failures: [{element, id, reason}],
        interpretedSize: {widthCm, heightCm, unitBasis, ppi},
        error: <str|None>,
      }
    """
    objects = []
    failures = []

    try:
        svg = SVG.parse(io.StringIO(svg_text), ppi=PPI)
    except Exception as exc:
        return {
            "objects": [], "importedCount": 0, "failedCount": 0, "failures": [],
            "interpretedSize": None,
            "error": f"Could not parse SVG: {exc}",
        }

    index = 0
    for element in svg.elements():
        if not isinstance(element, Shape):
            continue
        tag = (getattr(element, "values", {}) or {}).get("tag") \
            or type(element).__name__.lower()
        elem_id = getattr(element, "id", None)
        try:
            path = abs(Path(element))
            if len(path) == 0:
                continue
            rings = _flatten(path)
            result = _largest_ring_cm(rings)
            if result is None:
                failures.append({
                    "element": tag, "id": elem_id,
                    "reason": "no usable closed geometry (degenerate/empty)",
                })
                continue
            points, _area = result
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            min_x, min_y = min(xs), min(ys)
            width = round(max(xs) - min_x, 6)
            height = round(max(ys) - min_y, 6)
            if width <= 1e-6 or height <= 1e-6:
                failures.append({
                    "element": tag, "id": elem_id,
                    "reason": "zero-size bounding box",
                })
                continue
            index += 1
            objects.append({
                "id": elem_id or f"svg-{index:03d}",
                "type": "polygon",          # engine input (points-based)
                "svgType": tag,              # original element kind (display)
                "index": index,
                "points": points,            # absolute cm (transforms applied)
                "width": width,
                "height": height,
                "x0": round(min_x, 6),
                "y0": round(min_y, 6),
            })
        except Exception as exc:
            failures.append({
                "element": tag, "id": elem_id, "reason": str(exc),
            })

    interpreted = None
    if objects:
        all_x = [p[0] for o in objects for p in o["points"]]
        all_y = [p[1] for o in objects for p in o["points"]]
        interpreted = {
            "widthCm": round(max(all_x) - min(all_x), 4),
            "heightCm": round(max(all_y) - min(all_y), 4),
            "unitBasis": _detect_unit_basis(svg_text),
            "ppi": PPI,
        }

    error = None
    if not objects:
        error = "No supported/valid geometry found in the SVG."

    return {
        "objects": objects,
        "importedCount": len(objects),
        "failedCount": len(failures),
        "failures": failures,
        "interpretedSize": interpreted,
        "error": error,
    }
