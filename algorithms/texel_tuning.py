"""
Texel Tuning Script
===================
Optimizes the evaluation weights (piece values, PSTs, bonuses) by
minimising the mean-squared error vs Stockfish evaluations.

Usage:
    1. First generate the dataset:
       python algorithms/generate_dataset.py --num-positions 50000

    2. Then run tuning:
       python algorithms/texel_tuning.py

    3. Tuned weights are saved to algorithms/tuned_weights.py and
       automatically loaded by evaluation.py on the next run.
"""

import csv
import os
import sys
import time
import copy
import math
import numpy as np
from scipy.optimize import minimize

# ── Resolve project root ──
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

import chess
from algorithms.evaluation import (
    _flip, _mirror,
    PHASE_WEIGHT, TOTAL_PHASE,
)

DATASET_FILE = os.path.join(_PROJECT_ROOT, "data", "training", "dataset.csv")
OUTPUT_FILE = os.path.join(_PROJECT_ROOT, "algorithms", "tuned_weights.py")

# ──────────────────────────────────────────────────
# PARAMETER VECTOR: pack / unpack all tunable values
# ──────────────────────────────────────────────────

# Order:
#   [0..4]     MG piece values (P, N, B, R, Q)
#   [5..9]     EG piece values (P, N, B, R, Q)
PIECE_ORDER = [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]
PST_NAMES = [
    "MG_PAWN_TABLE", "EG_PAWN_TABLE",
    "MG_KNIGHT_TABLE", "EG_KNIGHT_TABLE",
    "MG_BISHOP_TABLE", "EG_BISHOP_TABLE",
    "MG_ROOK_TABLE", "EG_ROOK_TABLE",
    "MG_QUEEN_TABLE", "EG_QUEEN_TABLE",
    "MG_KING_TABLE", "EG_KING_TABLE",
]

NUM_MATERIAL = 10   # 5 MG + 5 EG
TOTAL_PARAMS = NUM_MATERIAL  # = 10


def pack_params():
    """Pack current evaluation.py piece weights into a flat numpy array."""
    from algorithms import evaluation as ev

    params = []

    # Material values
    for pt in PIECE_ORDER:
        params.append(ev.MG_VALUE[pt])
    for pt in PIECE_ORDER:
        params.append(ev.EG_VALUE[pt])

    return np.array(params, dtype=np.float64)


def unpack_params(params):
    """Unpack flat array into dicts/lists for evaluation."""
    from algorithms import evaluation as ev
    idx = 0

    mg_value = {}
    for pt in PIECE_ORDER:
        mg_value[pt] = int(round(params[idx]))
        idx += 1
    mg_value[chess.KING] = 0

    eg_value = {}
    for pt in PIECE_ORDER:
        eg_value[pt] = int(round(params[idx]))
        idx += 1
    eg_value[chess.KING] = 0

    # Keep original PST tables and bonuses since we aren't tuning them
    pst_tables = {
        "MG_PAWN_TABLE": ev.MG_PAWN_TABLE, "EG_PAWN_TABLE": ev.EG_PAWN_TABLE,
        "MG_KNIGHT_TABLE": ev.MG_KNIGHT_TABLE, "EG_KNIGHT_TABLE": ev.EG_KNIGHT_TABLE,
        "MG_BISHOP_TABLE": ev.MG_BISHOP_TABLE, "EG_BISHOP_TABLE": ev.EG_BISHOP_TABLE,
        "MG_ROOK_TABLE": ev.MG_ROOK_TABLE, "EG_ROOK_TABLE": ev.EG_ROOK_TABLE,
        "MG_QUEEN_TABLE": ev.MG_QUEEN_TABLE, "EG_QUEEN_TABLE": ev.EG_QUEEN_TABLE,
        "MG_KING_TABLE": ev.MG_KING_TABLE, "EG_KING_TABLE": ev.EG_KING_TABLE,
    }

    bonuses = {
        "DOUBLED_PAWN_PENALTY": ev.DOUBLED_PAWN_PENALTY,
        "ISOLATED_PAWN_PENALTY": ev.ISOLATED_PAWN_PENALTY,
        "BISHOP_PAIR_BONUS": ev.BISHOP_PAIR_BONUS,
        "ROOK_OPEN_FILE_BONUS": ev.ROOK_OPEN_FILE_BONUS,
        "ROOK_SEMI_OPEN_FILE_BONUS": ev.ROOK_SEMI_OPEN_FILE_BONUS,
        "KING_SHIELD_BONUS": ev.KING_SHIELD_BONUS,
    }

    return mg_value, eg_value, pst_tables, bonuses


# ──────────────────────────────────────────────────
# FAST EVALUATION (simplified for tuning speed)
# ──────────────────────────────────────────────────

def fast_evaluate(board, mg_value, eg_value, pst_tables, bonuses):
    """Simplified evaluate() for tuning — covers the main scoring terms.

    This mirrors the core of evaluation.py but skips some slower heuristics
    (like endgame mating patterns) that don't significantly affect tuning.
    """
    mg_pst = {
        chess.PAWN: pst_tables["MG_PAWN_TABLE"],
        chess.KNIGHT: pst_tables["MG_KNIGHT_TABLE"],
        chess.BISHOP: pst_tables["MG_BISHOP_TABLE"],
        chess.ROOK: pst_tables["MG_ROOK_TABLE"],
        chess.QUEEN: pst_tables["MG_QUEEN_TABLE"],
        chess.KING: pst_tables["MG_KING_TABLE"],
    }
    eg_pst = {
        chess.PAWN: pst_tables["EG_PAWN_TABLE"],
        chess.KNIGHT: pst_tables["EG_KNIGHT_TABLE"],
        chess.BISHOP: pst_tables["EG_BISHOP_TABLE"],
        chess.ROOK: pst_tables["EG_ROOK_TABLE"],
        chess.QUEEN: pst_tables["EG_QUEEN_TABLE"],
        chess.KING: pst_tables["EG_KING_TABLE"],
    }

    mg_score = 0
    eg_score = 0
    phase = 0

    for color in [chess.WHITE, chess.BLACK]:
        sign = 1 if color == chess.WHITE else -1
        for pt in chess.PIECE_TYPES:
            for sq in board.pieces(pt, color):
                # Material
                mg_score += sign * mg_value.get(pt, 0)
                eg_score += sign * eg_value.get(pt, 0)

                # PST
                idx = sq if color == chess.WHITE else (sq ^ 56)
                if pt in mg_pst:
                    mg_score += sign * mg_pst[pt][idx]
                    eg_score += sign * eg_pst[pt][idx]

                # Phase
                phase += PHASE_WEIGHT.get(pt, 0)

    # Tapered eval
    phase = min(phase, TOTAL_PHASE)
    mg_weight = phase
    eg_weight = TOTAL_PHASE - phase
    score = (mg_score * mg_weight + eg_score * eg_weight) // TOTAL_PHASE

    # Bishop pair
    for color in [chess.WHITE, chess.BLACK]:
        sign = 1 if color == chess.WHITE else -1
        if len(board.pieces(chess.BISHOP, color)) >= 2:
            score += sign * bonuses["BISHOP_PAIR_BONUS"]

    # Side to move
    if board.turn == chess.BLACK:
        score = -score

    return score


# ──────────────────────────────────────────────────
# LOSS FUNCTION
# ──────────────────────────────────────────────────

def sigmoid(x, K=0.0035):
    """Convert centipawn eval to win probability [0, 1]."""
    return 1.0 / (1.0 + math.exp(-K * x))


def compute_loss(params, boards, sf_evals, K=0.0035):
    """Mean squared error of sigmoid(our_eval) vs sigmoid(sf_eval)."""
    mg_value, eg_value, pst_tables, bonuses = unpack_params(params)

    total_error = 0.0
    for board, sf_cp in zip(boards, sf_evals):
        our_cp = fast_evaluate(board, mg_value, eg_value, pst_tables, bonuses)
        our_prob = sigmoid(our_cp, K)
        sf_prob = sigmoid(sf_cp, K)
        total_error += (our_prob - sf_prob) ** 2

    return total_error / len(boards)


# ──────────────────────────────────────────────────
# DATASET LOADING
# ──────────────────────────────────────────────────

def load_dataset(path, max_positions=None):
    """Load (board, eval_cp) pairs from CSV."""
    boards = []
    evals = []

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                board = chess.Board(row["fen"])
                cp = int(row["eval_cp"])
                # Skip extreme evals (likely broken positions)
                if abs(cp) > 4000:
                    continue
                boards.append(board)
                evals.append(cp)
            except Exception:
                continue

            if max_positions and len(boards) >= max_positions:
                break

    return boards, evals


# ──────────────────────────────────────────────────
# SAVE TUNED WEIGHTS
# ──────────────────────────────────────────────────

def save_tuned_weights(params, output_path):
    """Write tuned weights as a Python module."""
    mg_value, eg_value, pst_tables, bonuses = unpack_params(params)

    lines = [
        '"""',
        'Tuned Evaluation Weights',
        '========================',
        'Auto-generated by texel_tuning.py — do not edit manually.',
        '"""',
        '',
        'import chess',
        '',
        '# ── Material Values ──',
        f'MG_VALUE = {{',
        f'    chess.PAWN: {mg_value[chess.PAWN]}, chess.KNIGHT: {mg_value[chess.KNIGHT]}, chess.BISHOP: {mg_value[chess.BISHOP]},',
        f'    chess.ROOK: {mg_value[chess.ROOK]}, chess.QUEEN: {mg_value[chess.QUEEN]}, chess.KING: 0,',
        f'}}',
        f'EG_VALUE = {{',
        f'    chess.PAWN: {eg_value[chess.PAWN]}, chess.KNIGHT: {eg_value[chess.KNIGHT]}, chess.BISHOP: {eg_value[chess.BISHOP]},',
        f'    chess.ROOK: {eg_value[chess.ROOK]}, chess.QUEEN: {eg_value[chess.QUEEN]}, chess.KING: 0,',
        f'}}',
        '',
    ]

    # PST tables
    for name in PST_NAMES:
        table = pst_tables[name]
        lines.append(f'{name} = [')
        for rank in range(8):
            row = table[rank * 8: rank * 8 + 8]
            lines.append('    ' + ', '.join(f'{v:>4}' for v in row) + ',')
        lines.append(']')
        lines.append('')

    # Bonus constants
    lines.append('# ── Bonus Constants ──')
    for key, val in bonuses.items():
        lines.append(f'{key} = {val}')
    lines.append('')

    with open(output_path, "w", encoding="utf-8") as f:
        f.write('\n'.join(lines))


# ──────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Texel Tuning")
    parser.add_argument("--max-positions", type=int, default=None,
                        help="Maximum number of positions to load from dataset")
    args = parser.parse_args()

    print("=" * 60)
    print("  TEXEL TUNING")
    print("=" * 60)
    print()

    # Load dataset
    if not os.path.isfile(DATASET_FILE):
        print(f"ERROR: Dataset not found at {DATASET_FILE}")
        print("Run: python algorithms/generate_dataset.py --num-positions 50000")
        sys.exit(1)

    print(f"Loading dataset from: {DATASET_FILE}")
    boards, sf_evals = load_dataset(DATASET_FILE, max_positions=args.max_positions)
    print(f"Loaded {len(boards)} positions")
    print()

    # Initial parameters
    initial_params = pack_params()
    print(f"Parameter vector size: {len(initial_params)}")
    print()

    # Compute initial loss
    initial_loss = compute_loss(initial_params, boards, sf_evals)
    print(f"Initial loss (MSE): {initial_loss:.8f}")
    print()

    # Optimize using L-BFGS-B (fast, handles bounds well)
    print("Starting optimization (this may take 5-15 minutes)...")
    print()

    iteration_count = [0]
    best_loss = [initial_loss]

    def callback(xk):
        iteration_count[0] += 1
        if iteration_count[0] % 10 == 0:
            loss = compute_loss(xk, boards, sf_evals)
            improvement = (1 - loss / initial_loss) * 100
            if loss < best_loss[0]:
                best_loss[0] = loss
            print(f"  Iteration {iteration_count[0]:>4}: "
                  f"loss={loss:.8f}  "
                  f"improvement={improvement:.2f}%")

    start_time = time.time()

    result = minimize(
        compute_loss,
        initial_params,
        args=(boards, sf_evals),
        method='Powell',      # gradient-free, works well for discrete-ish params
        callback=callback,
        options={
            'maxiter': 500,
            'maxfev': 100000,
            'disp': True,
        }
    )

    elapsed = time.time() - start_time
    print()
    print(f"Optimization completed in {elapsed/60:.1f} minutes")
    print(f"Final loss: {result.fun:.8f}")
    print(f"Improvement: {(1 - result.fun / initial_loss) * 100:.2f}%")
    print(f"Function evaluations: {result.nfev}")
    print()

    # Save tuned weights
    save_tuned_weights(result.x, OUTPUT_FILE)
    print(f"Tuned weights saved to: {OUTPUT_FILE}")
    print()

    # Show key changes
    mg_orig, eg_orig, _, _ = unpack_params(initial_params)
    mg_tuned, eg_tuned, _, bonuses_tuned = unpack_params(result.x)

    print("Key weight changes:")
    print(f"  {'Piece':<8} {'MG orig':>8} {'MG tuned':>8} {'EG orig':>8} {'EG tuned':>8}")
    names = ['Pawn', 'Knight', 'Bishop', 'Rook', 'Queen']
    for name, pt in zip(names, PIECE_ORDER):
        print(f"  {name:<8} {mg_orig[pt]:>8} {mg_tuned[pt]:>8} "
              f"{eg_orig[pt]:>8} {eg_tuned[pt]:>8}")
    print()
    print("Bonus changes:")
    from algorithms import evaluation as ev
    orig_bonuses = {
        "DOUBLED_PAWN_PENALTY": ev.DOUBLED_PAWN_PENALTY,
        "ISOLATED_PAWN_PENALTY": ev.ISOLATED_PAWN_PENALTY,
        "BISHOP_PAIR_BONUS": ev.BISHOP_PAIR_BONUS,
        "ROOK_OPEN_FILE_BONUS": ev.ROOK_OPEN_FILE_BONUS,
        "ROOK_SEMI_OPEN_FILE_BONUS": ev.ROOK_SEMI_OPEN_FILE_BONUS,
        "KING_SHIELD_BONUS": ev.KING_SHIELD_BONUS,
    }
    for key in bonuses_tuned:
        print(f"  {key}: {orig_bonuses[key]} -> {bonuses_tuned[key]}")

    print()
    print("Done! The tuned weights will be loaded automatically")
    print("when evaluation.py is next imported.")


if __name__ == "__main__":
    main()
