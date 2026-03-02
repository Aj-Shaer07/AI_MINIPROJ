import sys
import os
import importlib


def load_algorithms():
    """Robustly import the algorithms modules.

    This prefers importing modules as top-level names (so unqualified
    imports inside `algorithms/*.py` work), and falls back to
    package-qualified imports if needed.
    """
    # Project root is three levels up from this file (utils -> app -> backend -> project root)
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)

    # Add the algorithms directory to sys.path if it exists (it's a sibling of backend)
    ALGORITHMS_DIR = os.path.join(ROOT, "algorithms")
    if os.path.isdir(ALGORITHMS_DIR) and ALGORITHMS_DIR not in sys.path:
        sys.path.insert(0, ALGORITHMS_DIR)

    try:
        evaluation = importlib.import_module("evaluation")
        move_generation = importlib.import_module("move_generation")
        move_ordering = importlib.import_module("move_ordering")
        transposition = importlib.import_module("transposition")
        # import search last so its unqualified imports resolve
        search = importlib.import_module("search")
    except ModuleNotFoundError:
        evaluation = importlib.import_module("algorithms.evaluation")
        move_generation = importlib.import_module("algorithms.move_generation")
        move_ordering = importlib.import_module("algorithms.move_ordering")
        transposition = importlib.import_module("algorithms.transposition")
        search = importlib.import_module("algorithms.search")

    return {
        "evaluation": evaluation,
        "move_generation": move_generation,
        "move_ordering": move_ordering,
        "transposition": transposition,
        "search": search,
    }
