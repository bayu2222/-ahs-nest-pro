"""Candidate position generator.

Generates the discrete set of bottom-left anchor points (where a shape's local
bbox min corner may be placed) derived from already-placed objects. This is the
classic "corner point" heuristic: the origin plus points to the right of and
above each placed object (offset by the spacing gap).

Isolated here so smarter generators (e.g. No-Fit-Polygon edges) can replace it
without touching the placement loop.
"""

from typing import List, Tuple

Point = Tuple[float, float]


def generate_candidates(placed_bboxes: List[dict], spacing: float) -> List[Point]:
    if not placed_bboxes:
        return [(0.0, 0.0)]

    points = {(0.0, 0.0)}
    for b in placed_bboxes:
        right = round(b["maxX"] + spacing, 6)
        top = round(b["maxY"] + spacing, 6)
        left = round(b["minX"], 6)
        bottom = round(b["minY"], 6)
        points.add((right, bottom))  # to the right, same baseline
        points.add((left, top))      # directly above
        points.add((0.0, top))       # left column at this height

    # Deterministic ordering: bottom-most first, then left-most.
    return sorted(points, key=lambda p: (p[1], p[0]))
