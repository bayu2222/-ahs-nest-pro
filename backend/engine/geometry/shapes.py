"""Primitive shape constructors.

Every constructor returns a list of (x, y) vertices in centimeters whose
bounding box has its minimum corner at the origin (0, 0). This gives all
shapes a canonical "local" frame that the nesting layer can translate/rotate.

The design intentionally funnels every shape type into a plain polygon so that
SVG paths/polygons exported from CorelDRAW can be added later as just another
constructor returning the same (x, y) list.
"""

import math
from typing import List, Tuple

Point = Tuple[float, float]


def _normalize(points: List[Point]) -> List[Point]:
    """Shift a polygon so its bounding-box min corner sits at the origin."""
    min_x = min(p[0] for p in points)
    min_y = min(p[1] for p in points)
    return [(round(x - min_x, 6), round(y - min_y, 6)) for x, y in points]


def rectangle(width: float, height: float) -> List[Point]:
    return _normalize([(0.0, 0.0), (width, 0.0), (width, height), (0.0, height)])


def circle(diameter: float, segments: int = 48) -> List[Point]:
    """Polygon approximation of a circle (irregular-shape engine uses polygons)."""
    r = diameter / 2.0
    pts = [
        (r + r * math.cos(2 * math.pi * i / segments),
         r + r * math.sin(2 * math.pi * i / segments))
        for i in range(segments)
    ]
    return _normalize(pts)


def triangle(width: float, height: float) -> List[Point]:
    """Isosceles triangle with apex centered on top."""
    return _normalize([(0.0, 0.0), (width, 0.0), (width / 2.0, height)])


def polygon(points: List[Point]) -> List[Point]:
    """Arbitrary polygon. Accepts raw points (e.g. a future SVG path sampling)."""
    if len(points) < 3:
        raise ValueError("A polygon needs at least 3 points")
    return _normalize([(float(x), float(y)) for x, y in points])
