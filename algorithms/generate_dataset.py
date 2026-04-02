"""
Dataset Generator for Texel Tuning
===================================
Generates (FEN, stockfish_eval_cp) pairs by playing random games
and evaluating positions with Stockfish.

Usage:
    python algorithms/generate_dataset.py --num-positions 50000
"""

import chess
import csv
import os
import sys
import random
import time
import argparse

# ── Resolve paths ──
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Stockfish binary path
SF_PATHS = [
    os.path.join(_PROJECT_ROOT, "data", "stockfish", "stockfish",
                 "stockfish-windows-x86-64-avx2.exe"),
    os.path.join(_PROJECT_ROOT, "data", "stockfish", "stockfish.exe"),
]

OUTPUT_DIR = os.path.join(_PROJECT_ROOT, "data", "training")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "dataset.csv")


def find_stockfish():
    for p in SF_PATHS:
        if os.path.isfile(p):
            return p
    return None


def generate_random_position(max_moves=80):
    """Play a random game (with some intelligence) and return a position."""
    board = chess.Board()
    num_moves = random.randint(4, max_moves)

    for _ in range(num_moves):
        if board.is_game_over():
            break

        legal = list(board.legal_moves)
        if not legal:
            break

        # Slightly smarter than uniform random:
        # - Favour captures and checks (more interesting positions)
        # - But still mostly random for diversity
        captures = [m for m in legal if board.is_capture(m)]
        checks = [m for m in legal if board.gives_check(m)]
        interesting = list(set(captures + checks))

        if interesting and random.random() < 0.3:
            move = random.choice(interesting)
        else:
            move = random.choice(legal)

        board.push(move)

    return board


def evaluate_positions(num_positions, sf_depth=12):
    """Generate positions and evaluate them with Stockfish."""
    from stockfish import Stockfish

    sf_path = find_stockfish()
    if sf_path is None:
        print("ERROR: Stockfish binary not found!")
        print("Looked in:", SF_PATHS)
        sys.exit(1)

    print(f"Using Stockfish: {sf_path}")
    sf = Stockfish(sf_path, depth=sf_depth)
    sf.update_engine_parameters({"Threads": 1, "Hash": 64})

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    positions = []
    seen_fens = set()
    start_time = time.time()
    skipped = 0

    print(f"Generating {num_positions} positions at depth {sf_depth}...")
    print(f"Output: {OUTPUT_FILE}")
    print()

    while len(positions) < num_positions:
        board = generate_random_position()

        # Skip terminal positions
        if board.is_game_over():
            skipped += 1
            continue

        # Skip positions with very few pieces (tablebase territory)
        if chess.popcount(board.occupied) <= 4:
            skipped += 1
            continue

        # Enforce strict Quiescence (No checks, no legal captures for side to move)
        # to ensure static piece values actually matter.
        if board.is_check() or any(board.is_capture(m) for m in board.legal_moves):
            skipped += 1
            continue

        # Skip duplicate positions
        fen = board.fen()
        fen_key = " ".join(fen.split()[:4])  # position only, no clocks
        if fen_key in seen_fens:
            skipped += 1
            continue
        seen_fens.add(fen_key)

        # Evaluate with Stockfish
        try:
            sf.set_fen_position(fen)
            evaluation = sf.get_evaluation()
        except Exception as e:
            print(f"  Stockfish error: {e}, skipping...")
            skipped += 1
            continue

        # Only use centipawn evaluations (skip mate scores)
        if evaluation["type"] != "cp":
            # Convert mate to a large cp value
            mate_moves = evaluation["value"]
            if mate_moves > 0:
                cp_value = 10000 - abs(mate_moves) * 10
            else:
                cp_value = -10000 + abs(mate_moves) * 10
        else:
            cp_value = evaluation["value"]

        # Clamp extreme values
        cp_value = max(-5000, min(5000, cp_value))

        positions.append((fen, cp_value))

        # Progress
        n = len(positions)
        if n % 500 == 0:
            elapsed = time.time() - start_time
            rate = n / elapsed
            eta = (num_positions - n) / rate if rate > 0 else 0
            print(f"  {n:>6}/{num_positions}  "
                  f"({n*100//num_positions}%)  "
                  f"{rate:.1f} pos/sec  "
                  f"ETA: {eta/60:.1f} min  "
                  f"skipped: {skipped}")

    # Save to CSV
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["fen", "eval_cp"])
        for fen, cp in positions:
            writer.writerow([fen, cp])

    elapsed = time.time() - start_time
    print()
    print(f"Done! Generated {len(positions)} positions in {elapsed/60:.1f} min")
    print(f"Skipped {skipped} positions (terminal/duplicate/few pieces)")
    print(f"Saved to: {OUTPUT_FILE}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Stockfish-evaluated positions for Texel Tuning")
    parser.add_argument("--num-positions", type=int, default=50000,
                        help="Number of positions to generate (default: 50000)")
    parser.add_argument("--depth", type=int, default=12,
                        help="Stockfish search depth (default: 12)")
    args = parser.parse_args()

    evaluate_positions(args.num_positions, args.depth)


if __name__ == "__main__":
    main()
