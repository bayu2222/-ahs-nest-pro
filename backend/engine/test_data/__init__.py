"""Deterministic test-shape generators.

Generates random but REPRODUCIBLE sets of shapes (seeded) so benchmarks and
debugging are repeatable. Nothing here is hard-coded into the engine; it is a
pluggable input source, mirroring how real geometry will arrive from CorelDRAW.
"""

import math
import random
from typing import List

from ..nesting.base import ShapeObject

SHAPE_TYPES = ["rectangle", "circle", "triangle", "polygon"]


def _random_polygon_points(rng: random.Random, size: float) -> List[list]:
    """Irregular convex-ish polygon inside a `size` x `size` box."""
    n = rng.randint(5, 8)
    cx = cy = size / 2.0
    r = size / 2.0
    pts = []
    for i in range(n):
        ang = (2 * math.pi * i / n) + rng.uniform(-0.15, 0.15)
        rad = r * rng.uniform(0.6, 1.0)
        pts.append([cx + rad * math.cos(ang), cy + rad * math.sin(ang)])
    return pts


def generate_objects(count: int, seed: int = 42,
                     types: List[str] = None,
                     min_size: float = 6.0,
                     max_size: float = 28.0) -> List[ShapeObject]:
    rng = random.Random(seed)
    types = types or SHAPE_TYPES
    objects: List[ShapeObject] = []
    for i in range(count):
        t = rng.choice(types)
        oid = f"obj-{i + 1:03d}"
        w = round(rng.uniform(min_size, max_size), 3)
        h = round(rng.uniform(min_size, max_size), 3)
        if t == "circle":
            objects.append(ShapeObject.from_spec(oid, t, width=w, height=w))
        elif t == "triangle":
            objects.append(ShapeObject.from_spec(oid, t, width=w, height=h))
        elif t == "polygon":
            pts = _random_polygon_points(rng, max(w, h))
            objects.append(ShapeObject.from_spec(oid, t, points=pts))
        else:
            objects.append(ShapeObject.from_spec(oid, t, width=w, height=h))
    return objects
