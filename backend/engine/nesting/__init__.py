"""Nesting layer: candidate generation, scoring and placement strategies."""

from .base import (  # noqa: F401
    DebugRecord,
    NestingAlgorithm,
    NestOutcome,
    NestSettings,
    ShapeObject,
)
from .heuristic import BottomLeftFill  # noqa: F401
from .registry import ALGORITHMS, get_algorithm  # noqa: F401
