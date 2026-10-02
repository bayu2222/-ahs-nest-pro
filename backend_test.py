#!/usr/bin/env python3
"""
Backend smoke test for AHS Nesting Engine V0.1
Tests all endpoints after svgelements dependency fix
"""

import os
import sys
import requests
import json

# Get base URL from environment or use default
BASE_URL = os.getenv("REACT_APP_BACKEND_URL", "https://ahs-project-audit.preview.emergentagent.com")
API_BASE = f"{BASE_URL}/api"

def test_root_endpoint():
    """Test GET /api/"""
    print("\n=== Test 1: GET /api/ ===")
    try:
        response = requests.get(f"{API_BASE}/", timeout=10)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert data.get("engine") == "AHS Nesting Engine", f"Expected 'AHS Nesting Engine', got {data.get('engine')}"
        assert data.get("version") == "0.1", f"Expected '0.1', got {data.get('version')}"
        
        print("✅ PASS: Root endpoint working")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False

def test_algorithms_endpoint():
    """Test GET /api/algorithms"""
    print("\n=== Test 2: GET /api/algorithms ===")
    try:
        response = requests.get(f"{API_BASE}/algorithms", timeout=10)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "algorithms" in data, "Missing 'algorithms' key"
        assert "shapeTypes" in data, "Missing 'shapeTypes' key"
        
        algorithms = data["algorithms"]
        assert "bottom-left-fill" in algorithms, "Missing 'bottom-left-fill' algorithm"
        
        shape_types = data["shapeTypes"]
        required_shapes = ["rectangle", "circle", "triangle", "polygon"]
        for shape in required_shapes:
            assert shape in shape_types, f"Missing shape type: {shape}"
        
        print("✅ PASS: Algorithms endpoint working")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False

def test_generate_endpoint():
    """Test POST /api/generate"""
    print("\n=== Test 3: POST /api/generate ===")
    try:
        payload = {
            "count": 10,
            "seed": 42
        }
        response = requests.post(f"{API_BASE}/generate", json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response keys: {data.keys()}")
        print(f"Number of objects: {len(data.get('objects', []))}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "objects" in data, "Missing 'objects' key"
        
        objects = data["objects"]
        assert len(objects) == 10, f"Expected 10 objects, got {len(objects)}"
        
        # Check first object structure
        first_obj = objects[0]
        required_fields = ["id", "type", "points", "width", "height"]
        for field in required_fields:
            assert field in first_obj, f"Missing field '{field}' in object"
        
        print(f"Sample object: {json.dumps(objects[0], indent=2)}")
        print("✅ PASS: Generate endpoint working")
        return objects  # Return for use in nest test
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return None

def test_nest_endpoint(objects):
    """Test POST /api/nest"""
    print("\n=== Test 4: POST /api/nest ===")
    if not objects:
        print("❌ SKIP: No objects from generate test")
        return None
    
    try:
        payload = {
            "objects": objects,
            "settings": {
                "media_width": 120,
                "spacing": 0.3,
                "rotation_step": 5,
                "allow_rotation": True,
                "height_mode": "auto",
                "algorithm": "bottom-left-fill"
            },
            "debug": True
        }
        
        response = requests.post(f"{API_BASE}/nest", json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error response: {response.text}")
            return None
        
        data = response.json()
        print(f"Response keys: {data.keys()}")
        
        # Check required top-level keys
        assert "objects" in data, "Missing 'objects' key"
        assert "stats" in data, "Missing 'stats' key"
        assert "verification" in data, "Missing 'verification' key"
        assert "debug" in data, "Missing 'debug' key"
        
        # Check objects have placement data
        placed_objects = data["objects"]
        assert len(placed_objects) > 0, "No objects in response"
        
        first_placed = placed_objects[0]
        placement_fields = ["x", "y", "rotation", "width", "height"]
        for field in placement_fields:
            assert field in first_placed, f"Missing placement field '{field}'"
        
        # Check stats structure
        stats = data["stats"]
        stats_fields = ["mediaWidth", "usedHeight", "utilization", "processingTime", 
                       "objectCount", "placedCount", "failedPlacements", 
                       "candidatesTested", "algorithm"]
        for field in stats_fields:
            assert field in stats, f"Missing stats field '{field}'"
        
        print(f"Stats: {json.dumps(stats, indent=2)}")
        
        # Check verification structure
        verification = data["verification"]
        verification_fields = ["spacing", "minDistance", "violatingPairs", "pairsChecked", "pass", "method"]
        for field in verification_fields:
            assert field in verification, f"Missing verification field '{field}'"
        
        print(f"Verification: {json.dumps(verification, indent=2)}")
        
        # Check debug structure
        debug_data = data["debug"]
        debug_fields = ["candidates", "rejected", "collisions", "boundingBoxes"]
        for field in debug_fields:
            assert field in debug_data, f"Missing debug field '{field}'"
        
        print(f"Debug keys: {list(debug_data.keys())}")
        print("✅ PASS: Nest endpoint working with all required fields")
        return data
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_determinism(objects):
    """Test determinism: same input should produce same output"""
    print("\n=== Test 5: Determinism Test ===")
    if not objects:
        print("❌ SKIP: No objects from generate test")
        return False
    
    try:
        payload = {
            "objects": objects,
            "settings": {
                "media_width": 120,
                "spacing": 0.3,
                "rotation_step": 5,
                "allow_rotation": True,
                "height_mode": "auto",
                "algorithm": "bottom-left-fill"
            },
            "debug": False
        }
        
        # First call
        response1 = requests.post(f"{API_BASE}/nest", json=payload, timeout=30)
        assert response1.status_code == 200, f"First call failed: {response1.status_code}"
        data1 = response1.json()
        
        # Second call
        response2 = requests.post(f"{API_BASE}/nest", json=payload, timeout=30)
        assert response2.status_code == 200, f"Second call failed: {response2.status_code}"
        data2 = response2.json()
        
        # Compare objects placement
        objects1 = data1["objects"]
        objects2 = data2["objects"]
        
        assert len(objects1) == len(objects2), "Different number of objects"
        
        for i, (obj1, obj2) in enumerate(zip(objects1, objects2)):
            assert obj1["x"] == obj2["x"], f"Object {i}: x mismatch"
            assert obj1["y"] == obj2["y"], f"Object {i}: y mismatch"
            assert obj1["rotation"] == obj2["rotation"], f"Object {i}: rotation mismatch"
        
        print("✅ PASS: Determinism verified - identical inputs produce identical outputs")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False

def test_benchmark_endpoint():
    """Test POST /api/benchmark"""
    print("\n=== Test 6: POST /api/benchmark ===")
    try:
        payload = {
            "counts": [10],
            "seed": 42,
            "settings": {
                "media_width": 120,
                "spacing": 0.3,
                "rotation_step": 5,
                "allow_rotation": True,
                "height_mode": "auto",
                "algorithm": "bottom-left-fill"
            }
        }
        
        response = requests.post(f"{API_BASE}/benchmark", json=payload, timeout=60)
        print(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error response: {response.text}")
            return False
        
        data = response.json()
        print(f"Response keys: {data.keys()}")
        
        assert "results" in data, "Missing 'results' key"
        results = data["results"]
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        
        print(f"Benchmark result: {json.dumps(results[0], indent=2)}")
        print("✅ PASS: Benchmark endpoint working")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False

def main():
    print("=" * 80)
    print("AHS Nesting Engine V0.1 - Backend Smoke Test")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"API Base: {API_BASE}")
    
    results = {}
    
    # Test 1: Root endpoint
    results["root"] = test_root_endpoint()
    
    # Test 2: Algorithms endpoint
    results["algorithms"] = test_algorithms_endpoint()
    
    # Test 3: Generate endpoint
    generated_objects = test_generate_endpoint()
    results["generate"] = generated_objects is not None
    
    # Test 4: Nest endpoint
    nest_result = test_nest_endpoint(generated_objects)
    results["nest"] = nest_result is not None
    
    # Test 5: Determinism
    results["determinism"] = test_determinism(generated_objects)
    
    # Test 6: Benchmark endpoint
    results["benchmark"] = test_benchmark_endpoint()
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_flag in results.items():
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All backend smoke tests PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
