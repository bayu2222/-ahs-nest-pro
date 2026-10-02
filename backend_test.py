#!/usr/bin/env python3
"""
Backend API tests for AHS Nesting Engine - SVG Import Phase B
Tests all endpoints with exact assertions as per review requirements.
"""
import requests
import json
import math

# Base URL from frontend/.env
BASE_URL = "https://ahs-project-audit.preview.emergentagent.com/api"

def test_capabilities():
    """Test 1: GET /api/import-svg/capabilities"""
    print("\n=== Test 1: GET /api/import-svg/capabilities ===")
    resp = requests.get(f"{BASE_URL}/import-svg/capabilities")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    
    data = resp.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    # Check required fields
    assert "path" in data["elements"], "Missing 'path' in elements"
    assert "rect" in data["elements"], "Missing 'rect' in elements"
    assert "circle" in data["elements"], "Missing 'circle' in elements"
    assert "ellipse" in data["elements"], "Missing 'ellipse' in elements"
    assert "polygon" in data["elements"], "Missing 'polygon' in elements"
    assert "polyline" in data["elements"], "Missing 'polyline' in elements"
    
    assert "rotate" in data["transforms"], "Missing 'rotate' in transforms"
    assert data["defaultDpi"] == 96, f"Expected defaultDpi 96, got {data['defaultDpi']}"
    assert data["coordinateSystem"]["origin"] == "bottom-left", f"Expected origin 'bottom-left', got {data['coordinateSystem']['origin']}"
    
    print("✅ PASS: capabilities endpoint returns correct data")
    return True

def test_import_svg_basic():
    """Test 2: POST /api/import-svg with rect, compound path with hole, and circle"""
    print("\n=== Test 2: POST /api/import-svg - Basic import with Y-flip verification ===")
    
    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="50mm" viewBox="0 0 100 50">
        <rect id="r" x="10" y="10" width="20" height="10"/>
        <path id="frame" d="M 40 10 h 20 v 20 h -20 Z M 45 15 h 10 v 10 h -10 Z"/>
        <circle id="c" cx="80" cy="25" r="5"/>
    </svg>"""
    
    payload = {
        "svg": svg_content,
        "filename": "t.svg"
    }
    
    resp = requests.post(f"{BASE_URL}/import-svg", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    
    data = resp.json()
    print(f"Response summary: importedCount={data['importedCount']}, failedCount={data['failedCount']}")
    
    # Check counts
    assert data["importedCount"] == 3, f"Expected importedCount 3, got {data['importedCount']}"
    assert data["failedCount"] == 0, f"Expected failedCount 0, got {data['failedCount']}"
    
    # Check document metadata
    doc = data["document"]
    assert doc["unitBasis"] == "physical", f"Expected unitBasis 'physical', got {doc['unitBasis']}"
    assert doc["sourceUnit"] == "mm", f"Expected sourceUnit 'mm', got {doc['sourceUnit']}"
    assert doc["widthCm"] == 10, f"Expected widthCm 10, got {doc['widthCm']}"
    assert doc["heightCm"] == 5, f"Expected heightCm 5, got {doc['heightCm']}"
    
    # Check coordinate system
    coord = data["coordinateSystem"]
    assert coord["yAxis"] == "up", f"Expected yAxis 'up', got {coord['yAxis']}"
    
    # Find objects by id
    objects = {obj["id"]: obj for obj in data["objects"]}
    
    # Check rect "r" - Y FLIP CHECK
    print("\n--- Checking rect 'r' (Y-flip verification) ---")
    r = objects["r"]
    assert r["width"] == 2, f"Expected width 2, got {r['width']}"
    assert r["height"] == 1, f"Expected height 1, got {r['height']}"
    assert r["bbox"]["minX"] == 1, f"Expected bbox.minX 1, got {r['bbox']['minX']}"
    assert r["bbox"]["maxX"] == 3, f"Expected bbox.maxX 3, got {r['bbox']['maxX']}"
    # Y FLIP: 10mm from top in 50mm page => top edge at 4cm from bottom, bottom edge at 3cm
    assert r["bbox"]["minY"] == 3, f"Expected bbox.minY 3 (Y-flip check), got {r['bbox']['minY']}"
    assert r["bbox"]["maxY"] == 4, f"Expected bbox.maxY 4 (Y-flip check), got {r['bbox']['maxY']}"
    assert r["holes"] == [], f"Expected holes [], got {r['holes']}"
    print(f"✅ rect 'r': width={r['width']}, height={r['height']}, bbox={r['bbox']}, Y-flip verified")
    
    # Check compound path "frame" with hole
    print("\n--- Checking compound path 'frame' (hole detection) ---")
    frame = objects["frame"]
    assert len(frame["holes"]) == 1, f"Expected exactly 1 hole, got {len(frame['holes'])}"
    hole = frame["holes"][0]
    assert len(hole) == 4, f"Expected hole with 4 points, got {len(hole)}"
    
    # Area should be outer (4 cm²) - inner (1 cm²) = 3 cm²
    area_expected = 3.0
    area_tolerance = 0.1
    assert abs(frame["area"] - area_expected) < area_tolerance, f"Expected area ≈ {area_expected}, got {frame['area']}"
    
    assert frame["bbox"]["minX"] == 4, f"Expected bbox.minX 4, got {frame['bbox']['minX']}"
    assert frame["bbox"]["maxX"] == 6, f"Expected bbox.maxX 6, got {frame['bbox']['maxX']}"
    assert frame["bbox"]["minY"] == 2, f"Expected bbox.minY 2, got {frame['bbox']['minY']}"
    assert frame["bbox"]["maxY"] == 4, f"Expected bbox.maxY 4, got {frame['bbox']['maxY']}"
    print(f"✅ frame: holes={len(frame['holes'])}, area={frame['area']:.2f}, bbox={frame['bbox']}")
    
    # Verify hole is NOT a separate object
    assert len(objects) == 3, f"Expected 3 objects (hole should not be separate), got {len(objects)}"
    
    # Check circle "c"
    print("\n--- Checking circle 'c' (flattened) ---")
    c = objects["c"]
    assert abs(c["width"] - 1.0) < 0.1, f"Expected width ≈ 1, got {c['width']}"
    assert abs(c["height"] - 1.0) < 0.1, f"Expected height ≈ 1, got {c['height']}"
    assert len(c["points"]) > 10, f"Expected many points (flattened circle), got {len(c['points'])}"
    
    # Bbox center should be at (8.0, 2.5) - Y flipped from (80mm, 25mm) in 50mm page
    bbox_center_x = (c["bbox"]["minX"] + c["bbox"]["maxX"]) / 2
    bbox_center_y = (c["bbox"]["minY"] + c["bbox"]["maxY"]) / 2
    assert abs(bbox_center_x - 8.0) < 0.1, f"Expected bbox center X ≈ 8.0, got {bbox_center_x}"
    assert abs(bbox_center_y - 2.5) < 0.1, f"Expected bbox center Y ≈ 2.5, got {bbox_center_y}"
    print(f"✅ circle 'c': width={c['width']:.2f}, height={c['height']:.2f}, points={len(c['points'])}, center=({bbox_center_x:.2f}, {bbox_center_y:.2f})")
    
    # Check all objects have required keys
    for obj_id, obj in objects.items():
        required_keys = ["id", "index", "svgType", "type", "points", "holes", "width", "height", "bbox", "area", "warnings"]
        for key in required_keys:
            assert key in obj, f"Object '{obj_id}' missing key '{key}'"
    
    print("\n✅ PASS: Basic SVG import with Y-flip, holes, and flattened curves")
    return data["objects"]

def test_round_trip_nesting(imported_objects):
    """Test 3: Round-trip into nesting engine"""
    print("\n=== Test 3: Round-trip - Import SVG then nest ===")
    
    # Prepare objects for nesting
    nest_objects = [
        {
            "id": obj["id"],
            "type": "polygon",
            "points": obj["points"]
        }
        for obj in imported_objects
    ]
    
    payload = {
        "objects": nest_objects,
        "settings": {
            "media_width": 10,
            "height_mode": "auto",
            "spacing": 0.3,
            "rotation_step": 15,
            "allow_rotation": True,
            "max_angle": 360,
            "algorithm": "bottom-left-fill"
        },
        "debug": False
    }
    
    resp = requests.post(f"{BASE_URL}/nest", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    
    data = resp.json()
    print(f"Nesting result: placedCount={data['stats']['placedCount']}, failedPlacements={data['stats']['failedPlacements']}")
    
    assert data["stats"]["placedCount"] == 3, f"Expected placedCount 3, got {data['stats']['placedCount']}"
    assert data["stats"]["failedPlacements"] == 0, f"Expected failedPlacements 0, got {data['stats']['failedPlacements']}"
    assert data["verification"]["pass"] == True, f"Expected verification.pass true, got {data['verification']['pass']}"
    
    print("✅ PASS: Round-trip nesting successful - all 3 objects placed and verified")
    return True

def test_dpi_handling():
    """Test 4: DPI parameter handling"""
    print("\n=== Test 4: DPI handling ===")
    
    svg_px = """<svg xmlns="http://www.w3.org/2000/svg" width="400px" height="200px">
        <rect x="0" y="0" width="96" height="96"/>
    </svg>"""
    
    # Test 1: Default DPI (96)
    print("\n--- Test 4a: Default DPI (96) ---")
    resp = requests.post(f"{BASE_URL}/import-svg", json={"svg": svg_px})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    width_default = data["document"]["widthCm"]
    # 400px / 96 dpi * 2.54 cm/inch = 10.583... but we're checking the rect width
    # Actually the document width should be checked: 400px at 96dpi = 400/96*2.54 = 10.583...
    # But review says "width 2.54" - this might be referring to the rect width (96px at 96dpi)
    # Let me check the rect object
    rect_obj = data["objects"][0]
    rect_width = rect_obj["width"]
    assert abs(rect_width - 2.54) < 0.01, f"Expected rect width ≈ 2.54 cm (96px at 96dpi), got {rect_width}"
    print(f"✅ Default DPI (96): rect width = {rect_width:.4f} cm")
    
    # Test 2: DPI 72
    print("\n--- Test 4b: DPI 72 ---")
    resp = requests.post(f"{BASE_URL}/import-svg", json={"svg": svg_px, "dpi": 72})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    rect_obj = data["objects"][0]
    rect_width_72 = rect_obj["width"]
    expected_72 = 96 / 72 * 2.54  # 3.3867 cm
    assert abs(rect_width_72 - expected_72) < 0.01, f"Expected rect width ≈ {expected_72:.4f} cm (96px at 72dpi), got {rect_width_72}"
    print(f"✅ DPI 72: rect width = {rect_width_72:.4f} cm (expected ≈ {expected_72:.4f})")
    
    # Test 3: DPI 0 (should use 96 as fallback or error - review says "422")
    # Actually review says "With dpi: 0 -> 422" which suggests validation error
    print("\n--- Test 4c: DPI 0 (validation error) ---")
    resp = requests.post(f"{BASE_URL}/import-svg", json={"svg": svg_px, "dpi": 0})
    assert resp.status_code == 422, f"Expected 422 for dpi=0, got {resp.status_code}"
    print(f"✅ DPI 0: correctly returns 422 validation error")
    
    print("\n✅ PASS: DPI handling works correctly")
    return True

def test_transform_rotation():
    """Test 5: Transform (rotation)"""
    print("\n=== Test 5: Transform (rotation) ===")
    
    svg_rotated = """<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="50mm" viewBox="0 0 100 50">
        <rect x="45" y="20" width="10" height="10" transform="rotate(45 50 25)"/>
    </svg>"""
    
    resp = requests.post(f"{BASE_URL}/import-svg", json={"svg": svg_rotated})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    
    data = resp.json()
    obj = data["objects"][0]
    
    # After 45° rotation, a 10x10mm square should have width ≈ height ≈ 14.142mm (√2 * 10)
    expected_dim = 1.4142  # cm
    tolerance = 0.01
    
    assert abs(obj["width"] - expected_dim) < tolerance, f"Expected width ≈ {expected_dim}, got {obj['width']}"
    assert abs(obj["height"] - expected_dim) < tolerance, f"Expected height ≈ {expected_dim}, got {obj['height']}"
    
    # Area should remain 1.0 cm² (100 mm²)
    assert abs(obj["area"] - 1.0) < 0.01, f"Expected area ≈ 1.0, got {obj['area']}"
    
    print(f"✅ PASS: Rotation transform - width={obj['width']:.4f}, height={obj['height']:.4f}, area={obj['area']:.4f}")
    return True

def test_error_cases():
    """Test 6: Error handling"""
    print("\n=== Test 6: Error cases ===")
    
    # Test 6a: Invalid SVG syntax
    print("\n--- Test 6a: Invalid SVG syntax ---")
    resp = requests.post(f"{BASE_URL}/import-svg", json={"svg": "<svg><<<"})
    assert resp.status_code == 400, f"Expected 400 for invalid SVG, got {resp.status_code}"
    data = resp.json()
    assert "detail" in data, "Expected 'detail' in error response"
    assert "error" in data["detail"], "Expected 'error' in detail"
    assert data["detail"]["error"].startswith("Could not parse SVG"), f"Expected error starting with 'Could not parse SVG', got: {data['detail']['error']}"
    print(f"✅ Invalid SVG: correctly returns 400 with error: {data['detail']['error'][:50]}...")
    
    # Test 6b: No supported geometry
    print("\n--- Test 6b: No supported geometry (text and line) ---")
    svg_no_geom = """<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm">
        <text x="0" y="5">hi</text>
        <line x1="0" y1="0" x2="5" y2="5"/>
    </svg>"""
    resp = requests.post(f"{BASE_URL}/import-svg", json={"svg": svg_no_geom})
    assert resp.status_code == 400, f"Expected 400 for no geometry, got {resp.status_code}"
    data = resp.json()
    assert "detail" in data, "Expected 'detail' in error response"
    assert "error" in data["detail"], "Expected 'error' in detail"
    assert "No supported/valid geometry" in data["detail"]["error"], f"Expected 'No supported/valid geometry' in error, got: {data['detail']['error']}"
    assert "failures" in data["detail"], "Expected 'failures' in detail"
    assert len(data["detail"]["failures"]) > 0, "Expected non-empty failures list"
    # Check that line is in failures
    failure_elements = [f.get("element") for f in data["detail"]["failures"]]
    assert "line" in failure_elements, f"Expected 'line' in failures, got: {failure_elements}"
    print(f"✅ No geometry: correctly returns 400 with error and failures (line element)")
    
    # Test 6c: Missing svg field
    print("\n--- Test 6c: Missing 'svg' field ---")
    resp = requests.post(f"{BASE_URL}/import-svg", json={"filename": "test.svg"})
    assert resp.status_code == 422, f"Expected 422 for missing svg field, got {resp.status_code}"
    print(f"✅ Missing svg field: correctly returns 422 validation error")
    
    print("\n✅ PASS: All error cases handled correctly")
    return True

def test_v01_regression():
    """Test 7: V0.1 regression - existing endpoints unchanged"""
    print("\n=== Test 7: V0.1 Regression ===")
    
    # Test 7a: GET /api/
    print("\n--- Test 7a: GET /api/ ---")
    resp = requests.get(f"{BASE_URL}/")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "engine" in data or "name" in data, "Expected 'engine' or 'name' in root response"
    print(f"✅ GET /api/: {data.get('engine', data.get('name', 'N/A'))}")
    
    # Test 7b: GET /api/algorithms
    print("\n--- Test 7b: GET /api/algorithms ---")
    resp = requests.get(f"{BASE_URL}/algorithms")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    # Can be either a list or an object with algorithms/shapeTypes
    if isinstance(data, list):
        print(f"✅ GET /api/algorithms: {len(data)} algorithms")
    else:
        assert "algorithms" in data or "shapeTypes" in data, "Expected 'algorithms' or 'shapeTypes' in response"
        print(f"✅ GET /api/algorithms: {len(data.get('algorithms', []))} algorithms, {len(data.get('shapeTypes', []))} shape types")
    
    # Test 7c: POST /api/generate
    print("\n--- Test 7c: POST /api/generate ---")
    resp = requests.post(f"{BASE_URL}/generate", json={"count": 10, "seed": 42})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    # Can be either a direct list or an object with "objects" key
    if isinstance(data, list):
        generated_objects = data
    else:
        assert "objects" in data, "Expected 'objects' in generate response"
        generated_objects = data["objects"]
    assert len(generated_objects) == 10, f"Expected 10 objects, got {len(generated_objects)}"
    print(f"✅ POST /api/generate: generated {len(generated_objects)} objects")
    
    # Test 7d: POST /api/nest (determinism check)
    print("\n--- Test 7d: POST /api/nest (determinism) ---")
    nest_payload = {
        "objects": generated_objects,
        "settings": {
            "media_width": 20,
            "height_mode": "auto",
            "spacing": 0.3,
            "rotation_step": 15,
            "allow_rotation": True,
            "max_angle": 360,
            "algorithm": "bottom-left-fill"
        },
        "debug": False
    }
    
    # First call
    resp1 = requests.post(f"{BASE_URL}/nest", json=nest_payload)
    assert resp1.status_code == 200, f"Expected 200, got {resp1.status_code}"
    data1 = resp1.json()
    
    # Second call (should be identical)
    resp2 = requests.post(f"{BASE_URL}/nest", json=nest_payload)
    assert resp2.status_code == 200, f"Expected 200, got {resp2.status_code}"
    data2 = resp2.json()
    
    # Check determinism
    assert data1["stats"]["placedCount"] == data2["stats"]["placedCount"], "Determinism check failed: placedCount differs"
    height_key = "totalHeight" if "totalHeight" in data1["stats"] else "mediaHeight"
    assert data1["stats"][height_key] == data2["stats"][height_key], f"Determinism check failed: {height_key} differs"
    
    print(f"✅ POST /api/nest: determinism verified (placedCount={data1['stats']['placedCount']}, height={data1['stats'][height_key]:.2f})")
    
    # Test 7e: POST /api/benchmark
    print("\n--- Test 7e: POST /api/benchmark ---")
    resp = requests.post(f"{BASE_URL}/benchmark", json={"counts": [10], "seed": 42})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert "results" in data, "Expected 'results' in benchmark response"
    print(f"✅ POST /api/benchmark: completed successfully")
    
    print("\n✅ PASS: All V0.1 regression tests passed")
    return True

def main():
    """Run all tests"""
    print("=" * 80)
    print("AHS Nesting Engine - SVG Import Phase B - Backend API Tests")
    print("=" * 80)
    
    try:
        # Test 1: Capabilities
        test_capabilities()
        
        # Test 2: Basic import with Y-flip
        imported_objects = test_import_svg_basic()
        
        # Test 3: Round-trip nesting
        test_round_trip_nesting(imported_objects)
        
        # Test 4: DPI handling
        test_dpi_handling()
        
        # Test 5: Transform
        test_transform_rotation()
        
        # Test 6: Error cases
        test_error_cases()
        
        # Test 7: V0.1 regression
        test_v01_regression()
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
