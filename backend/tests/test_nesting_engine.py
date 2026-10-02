"""Backend tests for AHS Nesting Engine V0.1."""
import os
import math
import pytest
import requests
from shapely.geometry import Polygon

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ahs-nest-prototype.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

SETTINGS_AUTO = {
    "media_width": 120.0,
    "media_height": None,
    "height_mode": "auto",
    "spacing": 0.3,
    "rotation_step": 15.0,
    "allow_rotation": True,
    "max_angle": 360.0,
    "algorithm": "bottom-left-fill",
}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def generated_objects(session):
    r = session.post(f"{API}/generate", json={"count": 20, "seed": 1}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "objects" in data and len(data["objects"]) == 20
    return data["objects"]


# ---------- /api/algorithms ----------
def test_algorithms(session):
    r = session.get(f"{API}/algorithms", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "bottom-left-fill" in data["algorithms"]
    assert set(["rectangle", "circle", "triangle", "polygon"]).issubset(set(data["shapeTypes"]))


# ---------- /api/generate ----------
def test_generate_shape(generated_objects):
    for o in generated_objects:
        assert "id" in o and "type" in o and "points" in o
        assert "width" in o and "height" in o
        assert isinstance(o["points"], list) and len(o["points"]) >= 3


# ---------- /api/nest - main correctness ----------
@pytest.fixture(scope="module")
def nest_result(session, generated_objects):
    payload = {"objects": generated_objects, "settings": SETTINGS_AUTO}
    r = session.post(f"{API}/nest", json=payload, timeout=120)
    assert r.status_code == 200, r.text
    return r.json()


def test_nest_response_schema(nest_result):
    stats = nest_result["stats"]
    for k in ["mediaWidth", "mediaHeight", "usedWidth", "usedHeight",
              "utilization", "processingTime", "objectCount", "placedCount",
              "failedPlacements", "candidatesTested", "algorithm"]:
        assert k in stats, f"missing {k}"
    for o in nest_result["objects"]:
        for k in ["id", "x", "y", "rotation", "width", "height", "bbox", "placed"]:
            assert k in o


def test_nest_no_overlap_and_spacing(nest_result):
    spacing = SETTINGS_AUTO["spacing"]
    placed = [o for o in nest_result["objects"] if o.get("placed")]
    assert len(placed) > 0
    polys = [Polygon(o["rotatedPoints"]) for o in placed]
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            d = polys[i].distance(polys[j])
            assert d >= spacing - 1e-3, (
                f"spacing violation between {placed[i]['id']} and {placed[j]['id']}: {d}")


def test_nest_within_media(nest_result):
    mw = nest_result["stats"]["mediaWidth"]
    for o in nest_result["objects"]:
        if not o.get("placed"):
            continue
        poly = Polygon(o["rotatedPoints"])
        minx, miny, maxx, maxy = poly.bounds
        assert minx >= -1e-3 and miny >= -1e-3
        assert maxx <= mw + 1e-3


# ---------- determinism ----------
def test_nest_determinism(session, generated_objects):
    payload = {"objects": generated_objects, "settings": SETTINGS_AUTO}
    r1 = session.post(f"{API}/nest", json=payload, timeout=120).json()
    r2 = session.post(f"{API}/nest", json=payload, timeout=120).json()
    assert r1["stats"]["usedHeight"] == r2["stats"]["usedHeight"]
    assert r1["stats"]["placedCount"] == r2["stats"]["placedCount"]
    placements1 = sorted([(o["id"], o.get("x"), o.get("y"), o.get("rotation")) for o in r1["objects"]])
    placements2 = sorted([(o["id"], o.get("x"), o.get("y"), o.get("rotation")) for o in r2["objects"]])
    assert placements1 == placements2


# ---------- fixed-height ----------
def test_nest_fixed_height(session, generated_objects):
    settings = dict(SETTINGS_AUTO)
    settings["height_mode"] = "fixed"
    settings["media_height"] = 20.0
    payload = {"objects": generated_objects, "settings": settings}
    r = session.post(f"{API}/nest", json=payload, timeout=120)
    assert r.status_code == 200
    data = r.json()
    assert data["stats"]["failedPlacements"] > 0
    for o in data["objects"]:
        if o.get("placed"):
            poly = Polygon(o["rotatedPoints"])
            assert poly.bounds[3] <= 20.0 + 1e-3


# ---------- debug mode ----------
def test_nest_debug(session, generated_objects):
    # small set so debug payload stays small
    payload = {"objects": generated_objects[:8], "settings": SETTINGS_AUTO, "debug": True}
    r = session.post(f"{API}/nest", json=payload, timeout=120)
    assert r.status_code == 200
    data = r.json()
    assert "debug" in data
    for k in ["candidates", "rejected", "collisions", "boundingBoxes"]:
        assert k in data["debug"]
        assert isinstance(data["debug"][k], list)
    assert len(data["debug"]["boundingBoxes"]) > 0


# ---------- benchmark ----------
def test_benchmark(session):
    payload = {"counts": [10, 20], "settings": {**SETTINGS_AUTO, "rotation_step": 15.0}, "seed": 1}
    r = session.post(f"{API}/benchmark", json=payload, timeout=180)
    assert r.status_code == 200
    data = r.json()
    assert "results" in data and len(data["results"]) == 2
    for row in data["results"]:
        for k in ["objectCount", "processingTime", "usedHeight", "utilization",
                  "failedPlacements", "candidatesTested"]:
            assert k in row, f"missing {k} in benchmark row"


# =========================================================================
# Iteration 2: performance optimization + dynamic spacing verification
# =========================================================================

SETTINGS_V2 = {
    "media_width": 120.0,
    "media_height": None,
    "height_mode": "auto",
    "spacing": 0.3,
    "rotation_step": 5.0,
    "allow_rotation": True,
    "max_angle": 360.0,
    "algorithm": "bottom-left-fill",
}


def _gen(session, count, seed=7):
    r = session.post(f"{API}/generate", json={"count": count, "seed": seed}, timeout=30)
    assert r.status_code == 200
    return r.json()["objects"]


def _nest(session, objs, settings):
    r = session.post(f"{API}/nest", json={"objects": objs, "settings": settings}, timeout=180)
    assert r.status_code == 200, r.text
    return r.json()


def _assert_no_overlap_and_spacing(result, spacing, mw):
    placed = [o for o in result["objects"] if o.get("placed")]
    polys = [Polygon(o["rotatedPoints"]) for o in placed]
    for i in range(len(polys)):
        minx, _, maxx, _ = polys[i].bounds
        assert minx >= -1e-3 and maxx <= mw + 1e-3, f"out of media: {polys[i].bounds}"
        for j in range(i + 1, len(polys)):
            d = polys[i].distance(polys[j])
            assert d >= spacing - 1e-3, (
                f"spacing violation {placed[i]['id']}/{placed[j]['id']}: {d:.6f} < {spacing}"
            )


# ---------- verification object shape (dynamic spacing) ----------
def test_verification_object_spacing_03(session):
    objs = _gen(session, 20, seed=7)
    res = _nest(session, objs, SETTINGS_V2)
    v = res["verification"]
    for k in ["spacing", "minDistance", "violatingPairs", "pairsChecked", "pass", "method"]:
        assert k in v
    assert v["method"] == "shapely-polygon-distance"
    assert abs(v["spacing"] - 0.3) < 1e-9
    assert v["pass"] is True
    assert v["violatingPairs"] == 0
    assert v["minDistance"] >= 0.3 - 1e-3


def test_verification_object_spacing_10(session):
    objs = _gen(session, 20, seed=7)
    settings = {**SETTINGS_V2, "spacing": 1.0}
    res = _nest(session, objs, settings)
    v = res["verification"]
    assert abs(v["spacing"] - 1.0) < 1e-9
    assert v["pass"] is True
    assert v["violatingPairs"] == 0
    assert v["minDistance"] >= 1.0 - 1e-3


def test_verification_object_spacing_05(session):
    objs = _gen(session, 20, seed=7)
    settings = {**SETTINGS_V2, "spacing": 0.5}
    res = _nest(session, objs, settings)
    v = res["verification"]
    assert abs(v["spacing"] - 0.5) < 1e-9
    assert v["pass"] is True
    assert v["violatingPairs"] == 0
    assert v["minDistance"] >= 0.5 - 1e-3



# ---------- correctness at 20/50/100 ----------
@pytest.mark.parametrize("count", [20, 50, 100])
def test_correctness_counts(session, count):
    objs = _gen(session, count, seed=7)
    res = _nest(session, objs, SETTINGS_V2)
    stats = res["stats"]
    assert stats["placedCount"] == count, f"n={count} placed={stats['placedCount']}"
    assert stats["failedPlacements"] == 0
    _assert_no_overlap_and_spacing(res, SETTINGS_V2["spacing"], SETTINGS_V2["media_width"])
    assert res["verification"]["pass"] is True


# ---------- determinism including candidatesTested ----------
def test_determinism_v2(session):
    objs = _gen(session, 50, seed=7)
    r1 = _nest(session, objs, SETTINGS_V2)
    r2 = _nest(session, objs, SETTINGS_V2)
    assert r1["stats"]["usedHeight"] == r2["stats"]["usedHeight"]
    assert r1["stats"]["utilization"] == r2["stats"]["utilization"]
    assert r1["stats"]["candidatesTested"] == r2["stats"]["candidatesTested"]
    p1 = sorted([(o["id"], o.get("x"), o.get("y"), o.get("rotation")) for o in r1["objects"]])
    p2 = sorted([(o["id"], o.get("x"), o.get("y"), o.get("rotation")) for o in r2["objects"]])
    assert p1 == p2


# ---------- benchmark 20/50/100 ----------
def test_benchmark_v2_full(session):
    payload = {"counts": [20, 50, 100], "settings": SETTINGS_V2, "seed": 7}
    r = session.post(f"{API}/benchmark", json=payload, timeout=180)
    assert r.status_code == 200
    rows = r.json()["results"]
    assert len(rows) == 3
    for row, expected in zip(rows, [20, 50, 100]):
        assert row["objectCount"] == expected
        assert row["placedCount"] == expected, f"n={expected} placed={row.get('placedCount')}"
        assert row["failedPlacements"] == 0
        print(f"BENCH n={expected} time={row['processingTime']:.3f}s "
              f"cand={row['candidatesTested']} util={row['utilization']} "
              f"usedH={row['usedHeight']}")
