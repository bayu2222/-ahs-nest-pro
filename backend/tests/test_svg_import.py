"""SVG Import Phase B tests.

Unit tests call ``engine.svg_import.import_svg`` directly (no HTTP) so the
geometry/unit/axis conventions are verified at the module boundary. A small
set of HTTP tests smoke-test ``POST /api/import-svg``.

AHS convention under test: unit cm, origin bottom-left, +Y up.
"""
import math
import os

import pytest
import requests
from shapely.geometry import Polygon

from engine.svg_import import import_svg
from engine.svg_import.importer import CURVE_MAX_CHORD_CM
from engine.nesting.base import NestSettings, ShapeObject
from engine.nesting.registry import get_algorithm
from engine.nesting.verify import verify_spacing

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ahs-project-audit.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

NS = 'xmlns="http://www.w3.org/2000/svg"'
TOL = 1e-4  # cm


def svg_mm(body, w=100, h=50):
    """Document w x h mm with 1 user unit == 1 mm."""
    return f'<svg {NS} width="{w}mm" height="{h}mm" viewBox="0 0 {w} {h}">{body}</svg>'


def only(result):
    assert result["error"] is None, result
    assert result["importedCount"] == 1, result
    return result["objects"][0]


def poly_of(obj):
    return Polygon(obj["points"], obj["holes"])


def close(a, b, tol=TOL):
    return abs(a - b) <= tol


# --------------------------------------------------------------------------
# Units
# --------------------------------------------------------------------------
def test_rectangle_mm_units_and_y_flip():
    # 20x10 mm rect at (10,10) mm from TOP-left in a 100x50 mm page.
    o = only(import_svg(svg_mm('<rect id="r" x="10" y="10" width="20" height="10"/>')))
    assert o["id"] == "r" and o["svgType"] == "rect" and o["type"] == "polygon"
    assert close(o["width"], 2.0) and close(o["height"], 1.0)
    b = o["bbox"]
    # X unchanged: 10mm -> 1cm .. 3cm
    assert close(b["minX"], 1.0) and close(b["maxX"], 3.0)
    # Y flipped once: top edge at 10mm from top -> 4cm from bottom; bottom edge -> 3cm
    assert close(b["minY"], 3.0) and close(b["maxY"], 4.0)
    assert poly_of(o).is_valid and o["holes"] == []


def test_document_info_physical_units():
    r = import_svg(svg_mm('<rect x="0" y="0" width="100" height="50"/>'))
    d = r["document"]
    assert d["unitBasis"] == "physical" and d["sourceUnit"] == "mm"
    assert close(d["widthCm"], 10.0) and close(d["heightCm"], 5.0)
    assert close(d["flipReferenceHeightCm"], 5.0)
    assert r["coordinateSystem"]["origin"] == "bottom-left" and r["coordinateSystem"]["yAxis"] == "up"


def test_physical_units_are_exact():
    r = import_svg(svg_mm('<rect x="0" y="0" width="100" height="50"/>'))
    o = r["objects"][0]
    assert o["width"] == 10.0 and o["height"] == 5.0
    assert r["document"]["widthCm"] == 10.0 and r["document"]["heightCm"] == 5.0


def test_cm_units_are_identity():
    o = only(import_svg(f'<svg {NS} width="20cm" height="10cm" viewBox="0 0 20 10"><rect x="1" y="1" width="5" height="2"/></svg>'))
    assert close(o["width"], 5.0) and close(o["height"], 2.0)
    assert close(o["bbox"]["minX"], 1.0) and close(o["bbox"]["maxY"], 9.0) and close(o["bbox"]["minY"], 7.0)


def test_physical_units_independent_of_dpi():
    svg = svg_mm('<rect x="0" y="0" width="50" height="50"/>')
    a = only(import_svg(svg, dpi=96))
    b = only(import_svg(svg, dpi=72))
    assert close(a["width"], 5.0) and close(b["width"], 5.0)


def test_px_with_dpi():
    svg = f'<svg {NS} width="400px" height="200px"><rect x="0" y="0" width="96" height="96"/></svg>'
    o96 = only(import_svg(svg, dpi=96))
    assert close(o96["width"], 2.54)
    o72 = only(import_svg(svg, dpi=72))
    assert close(o72["width"], 96 * 2.54 / 72)
    d = import_svg(svg, dpi=72)["document"]
    assert d["unitBasis"] == "px" and d["dpi"] == 72 and close(d["heightCm"], 200 * 2.54 / 72)


def test_unitless_width_height_treated_as_px():
    o = only(import_svg(f'<svg {NS} width="192" height="96"><rect x="0" y="0" width="192" height="96"/></svg>'))
    assert close(o["width"], 5.08) and close(o["height"], 2.54)


def test_viewbox_only_fallback_and_offset():
    # No width/height: user units == px @ dpi. viewBox origin offset must be removed.
    r = import_svg(f'<svg {NS} viewBox="50 50 200 100"><rect x="50" y="50" width="96" height="48"/></svg>')
    o = only(r)
    assert r["document"]["unitBasis"] == "viewbox-fallback"
    assert close(o["width"], 2.54) and close(o["height"], 1.27)
    assert close(o["bbox"]["minX"], 0.0)
    # page height = 100px = 2.645833cm; rect occupies the top 1.27cm
    page_h = 100 * 2.54 / 96
    assert close(o["bbox"]["maxY"], page_h) and close(o["bbox"]["minY"], page_h - 1.27)


def test_viewbox_scales_to_viewport():
    # viewBox 0 0 10 5 mapped onto 100x50mm -> 1 user unit = 10mm
    o = only(import_svg(f'<svg {NS} width="100mm" height="50mm" viewBox="0 0 10 5"><rect x="0" y="0" width="1" height="1"/></svg>'))
    assert close(o["width"], 1.0) and close(o["height"], 1.0)


def test_no_size_no_viewbox_uses_content_extent():
    r = import_svg(f'<svg {NS}><rect x="0" y="0" width="96" height="96"/></svg>')
    o = only(r)
    assert r["document"]["unitBasis"] == "content-fallback"
    assert close(o["width"], 2.54) and close(o["bbox"]["minY"], 0.0)


# --------------------------------------------------------------------------
# Shapes
# --------------------------------------------------------------------------
def test_circle():
    o = only(import_svg(svg_mm('<circle id="c" cx="50" cy="25" r="10"/>')))
    assert o["svgType"] == "circle"
    assert close(o["width"], 2.0, 1e-3) and close(o["height"], 2.0, 1e-3)
    p = poly_of(o)
    assert p.is_valid
    assert close(p.area, math.pi * 1.0 ** 2, 0.01)  # flattened circle
    cx, cy = p.centroid.x, p.centroid.y
    assert close(cx, 5.0, 1e-3) and close(cy, 2.5, 1e-3)


def test_ellipse():
    o = only(import_svg(svg_mm('<ellipse cx="50" cy="25" rx="20" ry="10"/>')))
    assert close(o["width"], 4.0, 1e-3) and close(o["height"], 2.0, 1e-3)
    assert poly_of(o).is_valid


def test_polygon_vertices_flipped():
    # Triangle apex at TOP (y=0) in SVG -> apex must have the LARGEST y in AHS.
    o = only(import_svg(svg_mm('<polygon id="t" points="10,0 30,20 -10,20"/>')))
    pts = o["points"]
    assert len(pts) == 3
    apex = max(pts, key=lambda p: p[1])
    assert close(apex[0], 1.0) and close(apex[1], 5.0)
    assert close(o["width"], 4.0) and close(o["height"], 2.0)


def test_polyline_closed_implicitly():
    o = only(import_svg(svg_mm('<polyline points="0,0 20,0 20,10 0,10"/>')))
    assert close(o["width"], 2.0) and close(o["height"], 1.0)
    assert close(poly_of(o).area, 2.0)


def test_path_straight_lines_relative_commands():
    o = only(import_svg(svg_mm('<path d="M 10 10 h 30 v 20 h -30 Z"/>')))
    assert close(o["width"], 3.0) and close(o["height"], 2.0)
    b = o["bbox"]
    assert close(b["minX"], 1.0) and close(b["maxY"], 4.0) and close(b["minY"], 2.0)


def test_bezier_curve_flattened_within_tolerance():
    # Half-disc built from a cubic that approximates a semicircle of radius 20mm.
    k = 0.5523 * 20
    d = f"M 30 25 C 30 {25 - k}, {50 - k} 5, 50 5 C {50 + k} 5, 70 {25 - k}, 70 25 Z"
    o = only(import_svg(svg_mm(f'<path d="{d}"/>')))
    p = poly_of(o)
    assert p.is_valid
    assert close(o["width"], 4.0, 1e-2) and close(o["height"], 2.0, 1e-2)
    assert close(p.area, math.pi * 2.0 ** 2 / 2.0, 0.05)
    # sampling density: consecutive points no further apart than the documented chord
    pts = o["points"]
    gaps = [math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    curve_gaps = sorted(gaps)[:-1]  # the single straight closing edge is allowed to be long
    assert max(curve_gaps) <= CURVE_MAX_CHORD_CM * 1.05
    # flipped: the arc bulges upward (max y) in AHS
    assert close(o["bbox"]["maxY"], 4.5, 1e-2) and close(o["bbox"]["minY"], 2.5, 1e-2)


def test_arc_command():
    # Full disc radius 10mm from two arcs.
    o = only(import_svg(svg_mm('<path d="M 40 25 A 10 10 0 1 1 60 25 A 10 10 0 1 1 40 25 Z"/>')))
    p = poly_of(o)
    assert p.is_valid
    assert close(o["width"], 2.0, 1e-3) and close(o["height"], 2.0, 1e-3)
    assert close(p.area, math.pi, 0.01)
    assert close(p.centroid.x, 5.0, 1e-3) and close(p.centroid.y, 2.5, 1e-3)


# --------------------------------------------------------------------------
# Transforms
# --------------------------------------------------------------------------
def test_transform_translate():
    o = only(import_svg(svg_mm('<rect x="0" y="0" width="10" height="10" transform="translate(20,10)"/>')))
    b = o["bbox"]
    assert close(b["minX"], 2.0) and close(b["maxX"], 3.0)
    assert close(b["maxY"], 4.0) and close(b["minY"], 3.0)


def test_transform_rotate():
    # 10x10 square rotated 45deg about its centre -> bbox 10*sqrt(2), same centre.
    o = only(import_svg(svg_mm('<rect x="45" y="20" width="10" height="10" transform="rotate(45 50 25)"/>')))
    s = 10 * math.sqrt(2) / 10.0  # cm
    assert close(o["width"], s, 1e-3) and close(o["height"], s, 1e-3)
    p = poly_of(o)
    assert close(p.centroid.x, 5.0, 1e-3) and close(p.centroid.y, 2.5, 1e-3)
    assert close(p.area, 1.0, 1e-3)


def test_transform_scale_and_nested_group():
    o = only(import_svg(svg_mm('<g transform="translate(10,10)"><g transform="scale(2)"><rect x="0" y="0" width="5" height="5"/></g></g>')))
    assert close(o["width"], 1.0) and close(o["height"], 1.0)
    assert close(o["bbox"]["minX"], 1.0) and close(o["bbox"]["maxY"], 4.0)


def test_transform_matrix():
    o = only(import_svg(svg_mm('<rect x="0" y="0" width="10" height="10" transform="matrix(2 0 0 1 10 0)"/>')))
    assert close(o["width"], 2.0) and close(o["height"], 1.0) and close(o["bbox"]["minX"], 1.0)


# --------------------------------------------------------------------------
# Compound paths / holes
# --------------------------------------------------------------------------
def test_compound_path_hole_preserved():
    d = "M 10 10 h 40 v 40 h -40 Z M 20 20 h 20 v 20 h -20 Z"
    r = import_svg(svg_mm(d and f'<path id="frame" d="{d}"/>'))
    o = only(r)
    assert len(o["holes"]) == 1, "hole must stay an interior ring"
    assert len(o["points"]) == 4 and len(o["holes"][0]) == 4
    p = poly_of(o)
    assert p.is_valid and len(p.interiors) == 1
    assert close(p.area, 16.0 - 4.0)
    assert close(o["area"], 12.0)
    # hole position is flipped consistently with the shell (centred here)
    hole = Polygon(o["holes"][0])
    assert close(hole.centroid.x, 3.0) and close(hole.centroid.y, 2.0)
    assert o["warnings"] == []


def test_compound_path_multiple_holes():
    d = ("M 0 0 h 60 v 30 h -60 Z "
         "M 10 10 h 10 v 10 h -10 Z "
         "M 40 10 h 10 v 10 h -10 Z")
    o = only(import_svg(svg_mm(f'<path d="{d}"/>')))
    assert len(o["holes"]) == 2
    assert close(o["area"], 18.0 - 2.0)
    assert poly_of(o).is_valid


def test_compound_path_disjoint_subpaths_single_object():
    # 'i'-like: two disjoint outers -> ONE object (largest) + warning, never two objects.
    d = "M 0 10 h 10 v 40 h -10 Z M 0 0 h 10 v 5 h -10 Z"
    r = import_svg(svg_mm(f'<path d="{d}"/>'))
    o = only(r)
    assert close(o["area"], 4.0) and o["holes"] == []
    assert any("disjoint" in w for w in o["warnings"])


def test_hole_is_not_a_separate_nesting_object_and_engine_accepts_exterior():
    d = "M 10 10 h 40 v 40 h -40 Z M 20 20 h 20 v 20 h -20 Z"
    r = import_svg(svg_mm(f'<path id="frame" d="{d}"/><rect id="solid" x="60" y="0" width="20" height="20"/>'))
    assert r["importedCount"] == 2
    objs = [ShapeObject.from_spec(o["id"], "polygon", points=[tuple(p) for p in o["points"]]) for o in r["objects"]]
    out = get_algorithm().nest(objs, NestSettings(media_width=20.0, spacing=0.3))
    assert out.placed_count == 2 and out.failed_placements == 0
    ver = verify_spacing([Polygon(o.rotated_points) for o in out.objects if o.placed], 0.3)
    assert ver["pass"] is True


# --------------------------------------------------------------------------
# Validity / errors / misc
# --------------------------------------------------------------------------
def test_all_outputs_valid_and_oriented():
    body = ('<rect x="0" y="0" width="10" height="10"/>'
            '<circle cx="30" cy="10" r="5"/>'
            '<path d="M 50 0 h 20 v 20 h -20 Z M 55 5 h 10 v 10 h -10 Z"/>'
            '<polygon points="80,0 95,0 90,15"/>')
    r = import_svg(svg_mm(body))
    assert r["importedCount"] == 4 and r["failedCount"] == 0
    for i, o in enumerate(r["objects"], start=1):
        assert o["index"] == i
        p = poly_of(o)
        assert p.is_valid and p.area > 0
        assert p.exterior.is_ccw, "exterior must be CCW (deterministic orientation)"
        for ring in p.interiors:
            assert not ring.is_ccw
        assert 0 <= o["bbox"]["minY"] and o["bbox"]["maxY"] <= 5.0 + TOL


def test_unsupported_elements_reported_not_imported():
    r = import_svg(svg_mm('<rect x="0" y="0" width="10" height="10"/><line x1="0" y1="0" x2="10" y2="10"/><text x="1" y="1">T</text>'))
    assert r["importedCount"] == 1
    assert r["failedCount"] == 1 and r["failures"][0]["element"] == "line"


def test_degenerate_zero_area_rect_fails_gracefully():
    r = import_svg(svg_mm('<rect x="0" y="0" width="10" height="0"/>'))
    assert r["importedCount"] == 0 and r["error"]


def test_invalid_svg():
    r = import_svg("<svg><<<not xml")
    assert r["objects"] == [] and r["error"].startswith("Could not parse SVG")


def test_empty_input_and_no_geometry():
    assert import_svg("   ")["error"] == "Empty SVG input."
    r = import_svg(f'<svg {NS} width="10mm" height="10mm"><text x="0" y="5">hi</text></svg>')
    assert r["importedCount"] == 0 and "No supported/valid geometry" in r["error"]


def test_deterministic_output():
    svg = svg_mm('<circle cx="50" cy="25" r="10"/><path d="M 0 0 C 10 20 30 20 40 0 Z"/>')
    assert import_svg(svg) == import_svg(svg)


# --------------------------------------------------------------------------
# HTTP endpoint smoke tests
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def test_api_capabilities(session):
    r = session.get(f"{API}/import-svg/capabilities", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "path" in d["elements"] and "rotate" in d["transforms"]
    assert d["defaultDpi"] == 96 and d["coordinateSystem"]["origin"] == "bottom-left"


def test_api_import_svg_success_and_nest_roundtrip(session):
    svg = svg_mm('<rect id="a" x="0" y="0" width="30" height="20"/>'
                 '<circle id="b" cx="60" cy="20" r="10"/>'
                 '<path id="c" d="M 0 30 h 20 v 15 h -20 Z M 5 35 h 10 v 5 h -10 Z"/>')
    r = session.post(f"{API}/import-svg", json={"svg": svg, "filename": "t.svg"}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["importedCount"] == 3 and d["failedCount"] == 0 and d["filename"] == "t.svg"
    assert d["document"]["unitBasis"] == "physical" and d["coordinateSystem"]["yAxis"] == "up"
    ids = [o["id"] for o in d["objects"]]
    assert ids == ["a", "b", "c"]
    for o in d["objects"]:
        for k in ("index", "bbox", "width", "height", "points", "holes", "area", "svgType"):
            assert k in o
    assert len(d["objects"][2]["holes"]) == 1

    # geometry is directly consumable by the existing nesting pipeline
    payload = [{"id": o["id"], "type": "polygon", "points": o["points"]} for o in d["objects"]]
    settings = {"media_width": 10.0, "height_mode": "auto", "spacing": 0.3,
                "rotation_step": 15.0, "allow_rotation": True, "max_angle": 360.0,
                "algorithm": "bottom-left-fill"}
    n = session.post(f"{API}/nest", json={"objects": payload, "settings": settings, "debug": False}, timeout=60)
    assert n.status_code == 200, n.text
    nd = n.json()
    assert nd["stats"]["placedCount"] == 3 and nd["stats"]["failedPlacements"] == 0
    assert nd["verification"]["pass"] is True


def test_api_import_svg_dpi_param(session):
    svg = f'<svg {NS} width="200px" height="100px"><rect x="0" y="0" width="72" height="72"/></svg>'
    r = session.post(f"{API}/import-svg", json={"svg": svg, "dpi": 72}, timeout=30)
    assert r.status_code == 200, r.text
    assert close(r.json()["objects"][0]["width"], 2.54)
    bad = session.post(f"{API}/import-svg", json={"svg": svg, "dpi": 0}, timeout=30)
    assert bad.status_code == 422


def test_api_import_svg_invalid_returns_400(session):
    r = session.post(f"{API}/import-svg", json={"svg": "<svg><<<"}, timeout=30)
    assert r.status_code == 400, r.text
    assert "Could not parse SVG" in r.json()["detail"]["error"]


def test_api_import_svg_no_geometry_returns_400(session):
    svg = f'<svg {NS} width="10mm" height="10mm"><text x="0" y="5">hi</text><line x1="0" y1="0" x2="5" y2="5"/></svg>'
    r = session.post(f"{API}/import-svg", json={"svg": svg}, timeout=30)
    assert r.status_code == 400, r.text
    det = r.json()["detail"]
    assert "No supported/valid geometry" in det["error"]
    assert det["failures"] and det["failures"][0]["element"] == "line"


def test_api_import_svg_partial_failures_200(session):
    svg = svg_mm('<rect x="0" y="0" width="10" height="10"/><line x1="0" y1="0" x2="5" y2="5"/>')
    r = session.post(f"{API}/import-svg", json={"svg": svg}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["importedCount"] == 1 and d["failedCount"] == 1
