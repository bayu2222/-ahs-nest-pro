"""Modular placement scoring.

Lower score = better placement. The default scorer encodes the V0.1 priorities:
  1. no overlap            (invalid placements never reach the scorer)
  2. minimum used height   (primary: top edge of the placed shape)
  3. compact placement     (secondary: left/bottom bias)
The weights are exposed so the scoring can be tuned later without touching the
nesting algorithm.
"""

from dataclasses import dataclass


@dataclass
class PlacementScorer:
    height_weight: float = 1000.0
    x_weight: float = 1.0
    y_weight: float = 0.01

    def score(self, x: float, y: float, w: float, h: float) -> float:
        top = y + h           # how tall the layout becomes with this placement
        return (
            self.height_weight * top
            + self.x_weight * x
            + self.y_weight * y
        )
