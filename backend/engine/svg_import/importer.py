"""SVG -> AHS Nest Pro geometry (Phase B).

This module is the ONLY place that knows about the SVG coordinate system. It
converts SVG elements into polygons expressed in the AHS internal convention
and hands them to the nesting pipeline as plain point lists. The nesting engine
never sees SVG units, transforms or axis orientation.

Coordinate conventions
----------------------
  SVG native : origin top-left, +Y down, user units resolved by viewBox/width.
  AHS        : unit cm, origin bottom-left, +Y up.
  The Y flip is applied EXACTLY ONCE here (``_to_ahs``) using the document
  height as reference:  y_ahs = H_doc_cm - y_svg_cm.

Unit strategy (deterministic)
-----------------------------
  svgelements resolves the whole document (viewBox, width/height, transforms)
  to CSS pixels at the requested ``dpi``. We convert px -> cm with
  ``2.54 / dpi``. Consequences:
    * physical root units (mm, cm, in, pt, pc) are exact and DPI-independent
      (the dpi cancels out);
    * px / unitless documents depend on ``dpi`` (default 96, configurable per
      request; CorelDRAW exports commonly use 96 or 72);
    * a viewBox is mapped onto the viewport (width/height). If only a viewBox
      exists, user units are treated as px at ``dpi`` ("viewbox-fallback").

Supported geometry
------------------
  path, rect, circle, ellipse, polygon, polyline. Every element is flattened to
  one polygon. Curves (cubic/quadratic Bezier, arcs) are sampled so that the
  distance between consecutive samples is <= ``CURVE_MAX_CHORD_CM`` (clamped to
  [CURVE_MIN_STEPS, CURVE_MAX_STEPS] samples per segment).

Compound paths / holes
----------------------
  Closed sub-paths are classified by even-odd containment depth. Depth 0 rings
  are outer boundaries, depth 1 rings become INTERIOR RINGS (holes) of their
  parent — never separate nesting objects. One SVG element yields one object;
  if an element contains several disjoint outer rings, the largest is kept and a
  warning is attached. The result is always a valid Shapely Polygon.
"""

from __future__ import annotations

import io
import math
import re
from typing import List, Optional, Tuple

from shapely.affinity import scale as _scale, translate as _translate
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient
from svgelements import SVG, Arc, Close, CubicBezier, Line, Move, Path
from svgelements import QuadraticBezier, Shape

# ----------------------------------------------------------------------------
# Documented constants
# ----------------------------------------------------------------------------
DEFAULT_DPI = 96.0           # CSS reference pixel density (px per inch)
CM_PER_INCH = 2.54
CURVE_MAX_CHORD_CM = 0.05    # <= 0.5 mm between consecutive curve samples
CURVE_MIN_STEPS = 8          # never fewer samples per curved segment
CURVE_MAX_STEPS = 128        # never more samples per curved segment
MIN_AREA_CM2 = 1e-6          # rings below this area are degenerate
COORD_DECIMALS = 6

SUPPORTED_ELEMENTS = ["path", "rect", "circle", "ellipse", "polygon", "polyline"]
SUPPORTED_TRANSFORMS = ["translate", "rotate", "scale", "matrix", "skewX", "skewY"]
PHYSICAL_UNITS = ("mm", "cm", "in", "pt", "pc")

COORDINATE_SYSTEM = {
    "unit": "cm",
    "origin": "bottom-left",
    "yAxis": "up",
    "note": "SVG (top-left, +Y down) is flipped exactly once at import: "
            "y_ahs = documentHeightCm - y_svg",
}

_LENGTH_RE = re.compile(r"^\s*([+-]?[0-9]*\.?[0-9]+(?:[eE][+-]?[0-9]+)?)\s*([a-zA-Z%]*)\s*$")

Point = Tuple[float, float]


# ----------------------------------------------------------------------------
# Helpers: units / document
# ----------------------------------------------------------------------------
def _split_length(raw) -> Tuple[Optional[float], Optional[str]]:
    """'100mm' -> (100.0, 'mm'); '200' -> (200.0, ''); None -> (None, None)."""
    if raw is None:
        return None, None
    m = _LENGTH_RE.match(str(raw))
    if not m:
        return None, None
    return float(m.group(1)), m.group(2).lower()


_UNIT_TO_CM = {"mm": 0.1, "cm": 1.0, "in": CM_PER_INCH, "pt": CM_PER_INCH / 72.0,
               "pc": CM_PER_INCH / 6.0}


def _document_info(svg, dpi: float) -> Tuple[dict, float]:
    """Describe the document and return (info, cm_per_px).

    For physical root units the px->cm factor is calibrated from the declared
    width (exact), which removes svgelements' internal rounding of mm->px.
    """
    cm_per_px = CM_PER_INCH / dpi
    raw_w = svg.values.get("width")
    raw_h = svg.values.get("height")
    val_w, unit_w = _split_length(raw_w)
    _, unit_h = _split_length(raw_h)
    unit = unit_w or unit_h or ""
    has_size = raw_w is not None and raw_h is not None and "%" not in str(raw_w) + str(raw_h)
    vb = svg.viewbox
    has_viewbox = vb is not None and vb.width and vb.height

    if has_size and unit in PHYSICAL_UNITS:
        basis = "physical"
        if val_w and unit_w in _UNIT_TO_CM and float(svg.width) > 0:
            cm_per_px = (val_w * _UNIT_TO_CM[unit_w]) / float(svg.width)
    elif has_size:
        basis = "px"
    elif has_viewbox:
        basis = "viewbox-fallback"
    else:
        basis = "content-fallback"

    width_cm = height_cm = None
    if has_size:
        width_cm = float(svg.width) * cm_per_px
        height_cm = float(svg.height) * cm_per_px
    elif has_viewbox:
        width_cm = float(vb.width) * cm_per_px
        height_cm = float(vb.height) * cm_per_px

    return {
        "sourceUnit": unit if has_size else None,
        "unitBasis": basis,
        "dpi": dpi,
        "cmPerPx": round(cm_per_px, 10),
        "hasViewBox": bool(has_viewbox),
        "viewBox": [vb.x, vb.y, vb.width, vb.height] if has_viewbox else None,
        "widthCm": round(width_cm, 6) if width_cm is not None else None,
        "heightCm": round(height_cm, 6) if height_cm is not None else None,
    }, cm_per_px


# ----------------------------------------------------------------------------
# Helpers: flattening
# ----------------------------------------------------------------------------
def _curve_steps(seg, cm_per_px: float) -> int:
    try:
        length_cm = float(seg.length(error=1e-3)) * cm_per_px
    except Exception:
        length_cm = 0.0
    if not math.isfinite(length_cm) or length_cm <= 0:
        return CURVE_MIN_STEPS
    steps = int(math.ceil(length_cm / CURVE_MAX_CHORD_CM))
    return max(CURVE_MIN_STEPS, min(CURVE_MAX_STEPS, steps))


def _flatten(path: Path, cm_per_px: float) -> List[List[Point]]:
    """Flatten an absolute Path into closed rings of (x, y) in SVG px."""
    rings: List[List[Point]] = []
    cur: List[Point] = []

    def _close():
        nonlocal cur
        if len(cur) >= 3:
            rings.append(cur)
        cur = []

    for seg in path:
        if isinstance(seg, Move):
            _close()
            if seg.end is not None:
                cur.append((seg.end.x, seg.end.y))
        elif isinstance(seg, Close):
            _close()
        elif isinstance(seg, Line):
            if seg.end is not None:
                cur.append((seg.end.x, seg.end.y))
        elif isinstance(seg, (CubicBezier, QuadraticBezier, Arc)):
            n = _curve_steps(seg, cm_per_px)
            for i in range(1, n + 1):
                p = seg.point(i / n)
                cur.append((p.x, p.y))
        else:  # unknown segment kind: keep its end point
            end = getattr(seg, "end", None)
            if end is not None:
                cur.append((end.x, end.y))
    _close()
    return rings


# ----------------------------------------------------------------------------
# Helpers: ring classification -> single valid polygon (holes preserved)
# ----------------------------------------------------------------------------
def _ring_polygon(ring_cm: List[Point]) -> Optional[Polygon]:
    try:
        poly = Polygon(ring_cm)
    except Exception:
        return None
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        return None
    if isinstance(poly, MultiPolygon):
        poly = max(poly.geoms, key=lambda g: g.area)
    if poly.area < MIN_AREA_CM2:
        return None
    return poly


def _rings_to_polygon(rings_cm: List[List[Point]]) -> Tuple[Optional[Polygon], List[str]]:
    """Combine the closed rings of ONE element into ONE valid polygon.

    Even-odd depth classification: depth 0 = outer, depth 1 = hole of its
    direct parent, depth >= 2 = nested island (ignored with a warning).
    """
    warnings: List[str] = []
    polys = [p for p in (_ring_polygon(r) for r in rings_cm) if p is not None]
    if not polys:
        return None, warnings
    if len(polys) == 1:
        return polys[0], warnings

    # sort largest first so parents precede children
    polys.sort(key=lambda p: -p.area)
    depth = [0] * len(polys)
    parent: List[Optional[int]] = [None] * len(polys)
    for i, p in enumerate(polys):
        # j contains i if the filled ring j covers ring i entirely (touching
        # allowed). Area tie-break guards against duplicated rings.
        containers = [
            j for j in range(len(polys))
            if j != i
            and (polys[j].area > p.area or (polys[j].area == p.area and j < i))
            and polys[j].covers(p)
        ]
        depth[i] = len(containers)
        if containers:
            # direct parent = smallest container
            parent[i] = min(containers, key=lambda j: polys[j].area)

    outers = [i for i in range(len(polys)) if depth[i] % 2 == 0]
    holes_of = {i: [] for i in outers}
    nested_islands = 0
    for i in range(len(polys)):
        if depth[i] % 2 == 1 and parent[i] in holes_of:
            holes_of[parent[i]].append(polys[i])
        elif depth[i] >= 2:
            nested_islands += 1
    if nested_islands:
        warnings.append(f"{nested_islands} nested island sub-path(s) inside holes ignored")

    built: List[Polygon] = []
    for i in outers:
        shell = polys[i].exterior.coords
        holes = [h.exterior.coords for h in holes_of[i]]
        poly = Polygon(shell, holes)
        if not poly.is_valid:
            poly = poly.buffer(0)
            if isinstance(poly, MultiPolygon):
                poly = max(poly.geoms, key=lambda g: g.area)
        if not poly.is_empty and poly.area >= MIN_AREA_CM2:
            built.append(poly)

    if not built:
        return None, warnings
    built.sort(key=lambda p: -p.area)
    if len(built) > 1:
        warnings.append(
            f"{len(built) - 1} disjoint outer sub-path(s) ignored (one object per SVG element)"
        )
    return built[0], warnings


# ----------------------------------------------------------------------------
# Helpers: coordinate system
# ----------------------------------------------------------------------------
def _to_ahs(poly: Polygon, doc_height_cm: float) -> Polygon:
    """SVG (y down) -> AHS (y up). Applied exactly once per polygon."""
    flipped = _translate(_scale(poly, xfact=1.0, yfact=-1.0, origin=(0, 0)), yoff=doc_height_cm)
    return orient(flipped, sign=1.0)  # CCW exterior, CW holes (deterministic)


def _coords(ring) -> List[List[float]]:
    pts = list(ring.coords)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    return [[round(x, COORD_DECIMALS), round(y, COORD_DECIMALS)] for x, y in pts]


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------
def import_svg(svg_text: str, dpi: float = DEFAULT_DPI) -> dict:
    """Parse SVG text into AHS polygon objects (cm, origin bottom-left, +Y up).

    Returns a dict (see module docstring for conventions)::

      {
        objects: [{id, index, svgType, type:'polygon', points, holes,
                   width, height, bbox{minX,minY,maxX,maxY}, area, warnings}],
        importedCount, failedCount, failures: [{element, id, reason}],
        document: {sourceUnit, unitBasis, dpi, cmPerPx, hasViewBox, viewBox,
                   widthCm, heightCm, flipReferenceHeightCm},
        coordinateSystem: {...}, supported: {elements, transforms},
        error: str | None,
      }

    ``points`` is the exterior ring (engine input); ``holes`` keeps interior
    rings so they are preserved without becoming separate nesting objects.
    """
    dpi = float(dpi) if dpi and dpi > 0 else DEFAULT_DPI
    base = {
        "objects": [], "importedCount": 0, "failedCount": 0, "failures": [],
        "document": None, "coordinateSystem": COORDINATE_SYSTEM,
        "supported": {"elements": SUPPORTED_ELEMENTS, "transforms": SUPPORTED_TRANSFORMS},
        "error": None,
    }

    if not svg_text or not svg_text.strip():
        return {**base, "error": "Empty SVG input."}

    try:
        svg = SVG.parse(io.StringIO(svg_text), ppi=dpi)
    except Exception as exc:
        return {**base, "error": f"Could not parse SVG: {exc}"}

    document, cm_per_px = _document_info(svg, dpi)

    # Pass 1: geometry in SVG orientation (cm)
    parsed = []       # (tag, elem_id, polygon_svg_cm, warnings)
    failures = []
    for element in svg.elements():
        if not isinstance(element, Shape):
            continue
        tag = (getattr(element, "values", {}) or {}).get("tag") or type(element).__name__.lower()
        elem_id = getattr(element, "id", None)
        try:
            path = abs(Path(element))
            if len(path) == 0:
                continue
            rings_px = _flatten(path, cm_per_px)
            rings_cm = [[(x * cm_per_px, y * cm_per_px) for (x, y) in r] for r in rings_px]
            poly, warnings = _rings_to_polygon(rings_cm)
            if poly is None:
                failures.append({"element": tag, "id": elem_id,
                                 "reason": "no usable closed geometry (degenerate/empty)"})
                continue
            parsed.append((tag, elem_id, poly, warnings))
        except Exception as exc:
            failures.append({"element": tag, "id": elem_id, "reason": str(exc)})

    # Flip reference: document height, else content extent
    if document["heightCm"] is not None:
        ref_h = document["heightCm"]
    elif parsed:
        ref_h = max(p.bounds[3] for _, _, p, _ in parsed)
    else:
        ref_h = 0.0
    document["flipReferenceHeightCm"] = round(ref_h, 6)

    # Pass 2: convert to AHS convention and serialize
    objects = []
    for tag, elem_id, poly_svg, warnings in parsed:
        poly = _to_ahs(poly_svg, ref_h)
        minx, miny, maxx, maxy = poly.bounds
        width = round(maxx - minx, COORD_DECIMALS)
        height = round(maxy - miny, COORD_DECIMALS)
        if width <= 1e-6 or height <= 1e-6:
            failures.append({"element": tag, "id": elem_id, "reason": "zero-size bounding box"})
            continue
        index = len(objects) + 1
        objects.append({
            "id": elem_id or f"svg-{index:03d}",
            "index": index,
            "svgType": tag,
            "type": "polygon",
            "points": _coords(poly.exterior),
            "holes": [_coords(r) for r in poly.interiors],
            "width": width,
            "height": height,
            "bbox": {
                "minX": round(minx, COORD_DECIMALS), "minY": round(miny, COORD_DECIMALS),
                "maxX": round(maxx, COORD_DECIMALS), "maxY": round(maxy, COORD_DECIMALS),
            },
            "area": round(poly.area, COORD_DECIMALS),
            "warnings": warnings,
        })

    if document["widthCm"] is None and objects:
        document["widthCm"] = round(max(o["bbox"]["maxX"] for o in objects), 6)
        document["heightCm"] = round(ref_h, 6)

    error = None
    if not objects:
        error = "No supported/valid geometry found in the SVG."

    return {
        **base,
        "objects": objects,
        "importedCount": len(objects),
        "failedCount": len(failures),
        "failures": failures,
        "document": document,
        "error": error,
    }
