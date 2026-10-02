"""Post-nesting spacing verification (debug / QA only).

Independent of the placement algorithm: it re-measures the ACTUAL geometric
distance between every pair of placed polygons using the same Shapely
`Polygon.distance` the collision checker uses (never bounding boxes), so the
reported numbers validate the engine's own output.
"""

from typing import List

from shapely.geometry import Polygon

# Tolerance below the configured spacing before a pair counts as a violation.
# Absorbs float rounding of placed coordinates (engine validates at EPS=1e-6).
VERIFY_TOL = 1e-4


def verify_spacing(placed_polys: List[Polygon], spacing: float) -> dict:
    n = len(placed_polys)
    min_dist = None
    violations = 0
    pairs = 0
    closest = None  # (i, j, distance)

    for i in range(n):
        for j in range(i + 1, n):
            pairs += 1
            d = placed_polys[i].distance(placed_polys[j])
            if min_dist is None or d < min_dist:
                min_dist = d
                closest = (i, j, d)
            if d < spacing - VERIFY_TOL:
                violations += 1

    return {
        "spacing": round(spacing, 6),
        "minDistance": round(min_dist, 6) if min_dist is not None else None,
        "violatingPairs": violations,
        "pairsChecked": pairs,
        "closestPair": (
            {"a": closest[0], "b": closest[1], "distance": round(closest[2], 6)}
            if closest is not None else None
        ),
        "pass": violations == 0,
        "method": "shapely-polygon-distance",
    }
