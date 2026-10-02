"""Optimization layer (placeholder for V0.1).

The heuristic produces an initial deterministic layout. This layer defines the
contract for future local optimization, simulated annealing or genetic
strategies that will refine an existing NestOutcome. Not implemented in V0.1.
"""

from ..nesting.base import NestOutcome, NestSettings, ShapeObject
from typing import List


class Optimizer:
    name: str = "none"

    def optimize(self, outcome: NestOutcome, settings: NestSettings) -> NestOutcome:
        """Return a (hopefully) improved layout. V0.1 is a no-op pass-through."""
        return outcome
