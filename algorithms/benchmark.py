"""
Self-Play Benchmark: Tuned vs Original Evaluation
==================================================
Plays N games between the tuned engine and the original (hardcoded) engine.
Properly swaps evaluation weights before each side's move.

Usage:
    python algorithms/benchmark.py --games 5 --depth 4
"""

import os
import sys
import time
import argparse

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

import chess
from algorithms.search import iterative_deepening
from algorithms.transposition import clear as tt_clear
import algorithms.evaluation as ev

# ── Save TUNED weights (loaded from tuned_weights.py via auto-import) ──
TUNED_MG = dict(ev.MG_VALUE)
TUNED_EG = dict(ev.EG_VALUE)

# ── ORIGINAL hardcoded weights (from evaluation.py source) ──
ORIG_MG = {
    chess.PAWN: 100, chess.KNIGHT: 337, chess.BISHOP: 365,
    chess.ROOK: 477, chess.QUEEN: 1025, chess.KING: 0,
}
ORIG_EG = {
    chess.PAWN: 120, chess.KNIGHT: 350, chess.BISHOP: 370,
    chess.ROOK: 530, chess.QUEEN: 1050, chess.KING: 0,
}


def set_weights(mg, eg):
    """Monkey-patch evaluation module to use specific piece values."""
    ev.MG_VALUE.update(mg)
    ev.EG_VALUE.update(eg)


def play_game(depth, tuned_is_white):
    """Play one game, swapping weights before each player's move.
    Returns 1.0 if tuned wins, 0.5 for draw, 0.0 if original wins.
    """
    board = chess.Board()
    move_count = 0
    max_moves = 200

    tt_clear()  # fresh TT per game

    while not board.is_game_over() and move_count < max_moves:
        is_white = board.turn == chess.WHITE
        use_tuned = (is_white == tuned_is_white)

        # Swap in the correct weights before searching
        if use_tuned:
            set_weights(TUNED_MG, TUNED_EG)
        else:
            set_weights(ORIG_MG, ORIG_EG)

        tt_clear()  # clear TT when switching engines so cached scores don't leak

        move, value, d, stats, elapsed = iterative_deepening(board, depth)
        if move is None:
            break

        board.push(move)
        move_count += 1

    # Restore tuned weights after the game
    set_weights(TUNED_MG, TUNED_EG)

    result = board.result()
    if result == "1-0":
        return 1.0 if tuned_is_white else 0.0
    elif result == "0-1":
        return 0.0 if tuned_is_white else 1.0
    else:
        return 0.5


def main():
    parser = argparse.ArgumentParser(description="Benchmark: Tuned vs Original")
    parser.add_argument("--games", type=int, default=5, help="Number of games")
    parser.add_argument("--depth", type=int, default=4, help="Search depth")
    args = parser.parse_args()

    print("=" * 60)
    print("  SELF-PLAY BENCHMARK: TUNED vs ORIGINAL")
    print(f"  Games: {args.games} | Depth: {args.depth}")
    print("=" * 60)
    print()
    print(f"  Tuned MG values:    P={TUNED_MG[chess.PAWN]} N={TUNED_MG[chess.KNIGHT]} "
          f"B={TUNED_MG[chess.BISHOP]} R={TUNED_MG[chess.ROOK]} Q={TUNED_MG[chess.QUEEN]}")
    print(f"  Original MG values: P={ORIG_MG[chess.PAWN]} N={ORIG_MG[chess.KNIGHT]} "
          f"B={ORIG_MG[chess.BISHOP]} R={ORIG_MG[chess.ROOK]} Q={ORIG_MG[chess.QUEEN]}")
    print()

    tuned_score = 0.0
    original_score = 0.0
    results = []

    for game_num in range(1, args.games + 1):
        tuned_is_white = (game_num % 2 == 1)
        color_str = "White" if tuned_is_white else "Black"
        print(f"Game {game_num}/{args.games}: Tuned plays {color_str}...", end=" ", flush=True)

        start = time.time()
        result = play_game(args.depth, tuned_is_white)
        elapsed = time.time() - start

        tuned_score += result
        original_score += (1.0 - result)

        if result == 1.0:
            outcome = "TUNED WINS"
        elif result == 0.0:
            outcome = "ORIGINAL WINS"
        else:
            outcome = "DRAW"

        results.append(outcome)
        print(f"{outcome} ({elapsed:.0f}s)")

    print()
    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print(f"  Tuned:    {tuned_score:.1f} / {args.games}")
    print(f"  Original: {original_score:.1f} / {args.games}")
    print()

    for i, r in enumerate(results, 1):
        color = "W" if (i % 2 == 1) else "B"
        print(f"  Game {i} (Tuned={color}): {r}")

    print()
    if tuned_score > original_score:
        print("  >>> TUNED engine is STRONGER! <<<")
    elif original_score > tuned_score:
        print("  >>> ORIGINAL engine is STRONGER! <<<")
    else:
        print("  >>> EVEN MATCH <<<")


if __name__ == "__main__":
    main()
