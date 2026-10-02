"""Algorithm registry so multiple strategies can be selected by name.

Future strategies (NFP-based packer, genetic/annealing optimizers) register
here and become available to the API/UI without code changes elsewhere.
"""

from .base import NestingAlgorithm
from .heuristic import BottomLeftFill

ALGORITHMS = {
    BottomLeftFill.name: BottomLeftFill,
}


def get_algorithm(name: str = BottomLeftFill.name) -> NestingAlgorithm:
    cls = ALGORITHMS.get(name, BottomLeftFill)
    return cls()
