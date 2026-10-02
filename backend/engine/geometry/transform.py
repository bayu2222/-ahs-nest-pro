"""Polygon transforms: rotation about the shape center, translation, bbox.

Kept separate from collision so rotation strategy can evolve independently.
"""

import math
from typing import List, Tuple

from shapely.affinity import rotate as _shapely_rotate
from shapely.affinity import translate as _shapely_translate
from shapely.geometry import Polygon

Point = Tuple[float, float]


def bounding_box(points: List[Point]) -> Tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def bbox_size(points: List[Point]) -> Tuple[float, float]:
    min_x, min_y, max_x, max_y = bounding_box(points)
    return (max_x - min_x, max_y - min_y)


def rotate_points(points: List[Point], angle_deg: float) -> List[Point]:
    """Rotate about the polygon's bounding-box center, then re-normalize so the
    rotated bounding box min corner is back at the origin.

    Rotation about the center keeps the shape visually in place; re-normalizing
    gives the caller a clean local frame + fresh bbox for the rotated shape.
    """
    if angle_deg % 360 == 0:
        return [(round(x, 6), round(y, 6)) for x, y in points]

    min_x, min_y, max_x, max_y = bounding_box(points)
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)

    rotated = []
    for x, y in points:
        dx, dy = x - cx, y - cy
        rotated.append((cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a))

    r_min_x = min(p[0] for p in rotated)
    r_min_y = min(p[1] for p in rotated)
    return [(round(x - r_min_x, 6), round(y - r_min_y, 6)) for x, y in rotated]


def to_polygon(points: List[Point], x: float = 0.0, y: float = 0.0) -> Polygon:
    """Build a shapely polygon translated to (x, y)."""
    poly = Polygon(points)
    if x != 0.0 or y != 0.0:
        poly = _shapely_translate(poly, xoff=x, yoff=y)
    return poly
