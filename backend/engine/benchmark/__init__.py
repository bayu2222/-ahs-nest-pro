"""Benchmark runner.

Runs the nesting engine over configurable object-count sets and records the
metrics requested by the spec: processing time, used height, utilization,
failed placements and candidate positions tested.
"""

from typing import List

from ..nesting.base import NestSettings
from ..nesting.registry import get_algorithm
from ..test_data import generate_objects


def run_benchmark(counts: List[int], settings: NestSettings,
                  seed: int = 42, algorithm: str = "bottom-left-fill") -> List[dict]:
    results = []
    algo = get_algorithm(algorithm)
    for c in counts:
        objects = generate_objects(c, seed=seed)
        outcome = algo.nest(objects, settings, debug=False)
        results.append({
            "objectCount": c,
            "placedCount": outcome.placed_count,
            "failedPlacements": outcome.failed_placements,
            "processingTime": outcome.processing_time,
            "usedHeight": outcome.used_height,
            "usedWidth": outcome.used_width,
            "utilization": outcome.utilization,
            "candidatesTested": outcome.candidates_tested,
        })
    return results
