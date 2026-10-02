"""Core data structures shared across the nesting layer.

These are plain dataclasses (UI/framework independent) so the engine can be
embedded anywhere later (e.g. the CorelDRAW plugin). All measurements are cm.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from shapely.geometry import Polygon

from ..geometry import shapes as shapes_mod
from ..geometry.transform import bbox_size

Point = Tuple[float, float]


@dataclass
class NestSettings:
    media_width: float = 120.0
    media_height: Optional[float] = None  # None + auto mode => computed
    height_mode: str = "auto"  # "auto" | "fixed"
    spacing: float = 0.3
    rotation_step: float = 5.0
    allow_rotation: bool = True
    max_angle: float = 360.0

    def effective_height(self) -> float:
        if self.height_mode == "fixed" and self.media_height:
            return self.media_height
        return math.inf

    def rotation_angles(self) -> List[float]:
        if not self.allow_rotation or self.rotation_step <= 0:
            return [0.0]
        angles = []
        a = 0.0
        while a < self.max_angle - 1e-9:
            angles.append(round(a, 6))
            a += self.rotation_step
        return angles


@dataclass
class ShapeObject:
    """A shape to nest. `points` is the base local polygon (bbox min at 0,0)."""

    id: str
    type: str
    points: List[Point]
    width: float
    height: float
    original_rotation: float = 0.0

    # Placement result (filled by the algorithm)
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    placed: bool = False
    rotated_points: Optional[List[Point]] = None
    bbox: Optional[dict] = None

    @property
    def area(self) -> float:
        return Polygon(self.points).area

    @property
    def longest_dimension(self) -> float:
        return max(self.width, self.height)

    @classmethod
    def from_spec(
        cls,
        id: str,
        type: str,
        width: float = 0.0,
        height: float = 0.0,
        points: Optional[List[Point]] = None,
        original_rotation: float = 0.0,
    ) -> "ShapeObject":
        if type == "rectangle":
            pts = shapes_mod.rectangle(width, height)
        elif type == "circle":
            pts = shapes_mod.circle(width)  # width used as diameter
        elif type == "triangle":
            pts = shapes_mod.triangle(width, height)
        elif type == "polygon":
            pts = shapes_mod.polygon(points or [])
        else:
            raise ValueError(f"Unknown shape type: {type}")
        w, h = bbox_size(pts)
        return cls(
            id=id,
            type=type,
            points=pts,
            width=round(w, 6),
            height=round(h, 6),
            original_rotation=original_rotation,
        )


@dataclass
class DebugRecord:
    candidates: List[dict] = field(default_factory=list)
    rejected: List[dict] = field(default_factory=list)
    collisions: List[dict] = field(default_factory=list)
    bounding_boxes: List[dict] = field(default_factory=list)


@dataclass
class NestOutcome:
    objects: List[ShapeObject]
    media_width: float
    media_height: float  # fixed value or computed used height (finite)
    used_width: float
    used_height: float
    utilization: float
    processing_time: float
    object_count: int
    placed_count: int
    failed_placements: int
    candidates_tested: int
    debug: Optional[DebugRecord] = None


class NestingAlgorithm:
    """Abstract base so multiple strategies can be registered and A/B tested."""

    name: str = "base"

    def nest(self, objects: List[ShapeObject], settings: NestSettings,
             debug: bool = False) -> NestOutcome:  # pragma: no cover
        raise NotImplementedError
