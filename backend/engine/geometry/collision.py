"""Collision, spacing and boundary tests using ACTUAL polygon geometry.

Bounding boxes are only used by callers for fast pre-rejection; the authoritative
checks here operate on real shapely polygons so irregular shapes are handled
correctly. Spacing is treated as a true geometric constraint (minimum metric
distance between polygons), never as a width/height padding hack.
"""

from typing import List

from shapely.geometry import Polygon

EPS = 1e-6


def within_media(poly: Polygon, media_width: float, media_height: float) -> bool:
    """True if the polygon lies completely inside [0,w] x [0,h].

    media_height may be math.inf for auto-height mode.
    """
    min_x, min_y, max_x, max_y = poly.bounds
    if min_x < -EPS or min_y < -EPS:
        return False
    if max_x > media_width + EPS:
        return False
    if max_y > media_height + EPS:
        return False
    return True


def respects_spacing(poly: Polygon, other: Polygon, spacing: float) -> bool:
    """True if `poly` keeps at least `spacing` cm from `other` AND does not overlap.

    shapely `distance` returns 0 when polygons touch or overlap, so a single
    distance check enforces both no-overlap and the spacing gap.
    """
    return poly.distance(other) >= spacing - EPS


def collides_any(poly: Polygon, others: List[Polygon], spacing: float) -> bool:
    """True if `poly` violates spacing/overlap against ANY polygon in `others`."""
    for other in others:
        if poly.distance(other) < spacing - EPS:
            return True
    return False


def overlap_area(poly: Polygon, other: Polygon) -> float:
    """Intersection area (cm^2) - used by debug mode to highlight collisions."""
    if not poly.intersects(other):
        return 0.0
    return poly.intersection(other).area
