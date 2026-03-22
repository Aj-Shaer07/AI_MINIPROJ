"""
Test Play: King + Bishop + Knight vs King Checkmate
=====================================================
Launches the pygame chess UI with various KBN endgame positions so you can
test whether the engine can force checkmate with Bishop and Knight.

You play the lone Black King.  The engine plays White (K + B + N).

The KBN mate is one of the hardest basic endgames — the engine must:
  1. Push the lone king to the edge
  2. Drive it to the CORRECT corner (matching the bishop's square colour)
  3. Deliver checkmate without stalemate

Presets
-------
  default     — black king in centre, pieces spread out (hardest for engine)
  edge        — black king already on edge, must be driven to correct corner
  wrong_corner — black king in the WRONG corner (engine must redirect)
  near_mate   — black king almost trapped in the correct corner (short mate)
  close       — all pieces clustered, engine should convert quickly
  a1_dark     — dark-sq bishop targets a1 corner (dark)
  h8_dark     — dark-sq bishop targets h8 corner (dark)
  a8_light    — light-sq bishop targets a8 corner (light)
  h1_light    — light-sq bishop targets h1 corner (light)

Usage:
    python UI/test_kbn_mate.py                        # default position
    python UI/test_kbn_mate.py --preset wrong_corner  # wrong corner test
    python UI/test_kbn_mate.py --preset near_mate     # near-mate position
    python UI/test_kbn_mate.py --fen "<custom FEN>"   # your own FEN
    python UI/test_kbn_mate.py --autoplay              # engine vs engine
"""

import sys
import os
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

UI_DIR = os.path.join(ROOT, "UI")
if UI_DIR not in sys.path:
    sys.path.insert(0, UI_DIR)

# ── preset KBN positions ─────────────────────────────────────────────
# All positions: White = K + B + N,  Black = K only.
# Bishop on c1 (dark sq) → correct corners are a1, h8
# Bishop on f1 (light sq) → correct corners are a8, h1

PRESETS = {
    # --- general tests ---
    "default":       "8/8/8/3k4/8/8/8/2N1KB2 w - - 0 1",
    # King e1, Bishop f1(light), Knight c1 — black king d5 centre

    "edge":          "4k3/8/8/8/8/8/8/2N1KB2 w - - 0 1",
    # Black king already on back rank e8

    "wrong_corner":  "8/8/8/8/8/5N2/8/2B1K2k w - - 0 1",
    # White: Ke1, Bc1(dark), Nf3.  Black: Kh1 (wrong corner for dark-sq bishop).
    # Engine must drive it toward a1 or h8.

    "near_mate":     "k1K5/8/1B6/N7/8/8/8/8 w - - 0 1",
    # Black king a8, White Kc8, Ba6→Bb6, Na5. Near-mate in correct corner.

    "close":         "8/8/8/8/3k4/4NB2/3K4/8 w - - 0 1",
    # All pieces close in centre — engine should corner the king quickly.

    # --- corner-specific tests (bishop colour determines correct corners) ---
    "a1_dark":       "8/8/8/8/8/2N5/8/B3K2k w - - 0 1",
    # Dark-sq bishop a1. Target corners a1 or h8. Black king h1 (wrong).

    "h8_dark":       "k7/8/8/8/8/2N5/8/B3K3 w - - 0 1",
    # Dark-sq bishop a1. Target a1/h8. Black king a8 (wrong).

    "a8_light":      "7k/8/8/8/8/2N5/8/4KB2 w - - 0 1",
    # Light-sq bishop f1. Target a8/h1. Black king h8 (wrong).

    "h1_light":      "k7/8/8/8/8/2N5/8/4KB2 w - - 0 1",
    # Light-sq bishop f1. Target a8/h1. Black king a8 (correct!).
    # Engine should finish this one more easily.
}


def list_presets():
    """Print all available presets with descriptions."""
    print("\nAvailable KBN presets:\n")
    print(f"  {'Preset':<16} {'FEN'}")
    print(f"  {'-'*14}   {'-'*45}")
    for name, fen in PRESETS.items():
        print(f"  {name:<16} {fen}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Test Play: Can the engine force checkmate with K+B+N vs K?"
    )
    parser.add_argument(
        "--preset", type=str, choices=list(PRESETS.keys()), default="default",
        help="Use a built-in preset position (default: 'default')."
    )
    parser.add_argument(
        "--fen", type=str, default=None,
        help="Custom starting FEN (overrides --preset)."
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all available presets and exit."
    )
    parser.add_argument(
        "--autoplay", action="store_true",
        help="Engine plays BOTH sides (engine vs engine) to verify mating."
    )
    args = parser.parse_args()

    if args.list:
        list_presets()
        return

    fen = args.fen if args.fen else PRESETS[args.preset]

    print("=" * 62)
    print("  KBN CHECKMATE TEST")
    print("=" * 62)
    print(f"  Preset : {args.preset}")
    print(f"  FEN    : {fen}")
    if args.autoplay:
        print(f"  Mode   : AUTO-PLAY (engine vs engine)")
    else:
        print(f"  Mode   : You play Black (lone King). Engine plays White.")
    print()
    print("  The engine must force checkmate with King + Bishop + Knight.")
    print("  Watch for: correct corner selection, stalemate avoidance,")
    print("  and the W-manoeuvre to drive the king to the right corner.")
    print("=" * 62)
    print()

    if args.autoplay:
        # Run engine-vs-engine in the terminal (no GUI)
        _run_autoplay(fen)
    else:
        # Clear sys.argv so UI/main.py's internal argparse doesn't see
        # our test-specific flags (--preset, --fen, etc.)
        sys.argv = [sys.argv[0]]

        # Launch the full pygame UI
        import main as ui_main
        ui_main.main(
            start_time=0,        # no clock
            increment=0,
            human_color="black", # you play the lone Black king
            fen=fen,
        )


def _run_autoplay(fen):
    """Engine plays both sides in the terminal until game over or 200 moves."""
    import chess
    import algorithms.search as engine_search

    board = chess.Board(fen)
    MAX_DEPTH = 6
    move_count = 0
    max_moves = 200

    print(f"Starting autoplay from: {fen}\n")
    print(board)
    print()

    while not board.is_game_over() and move_count < max_moves:
        engine_is_black = (board.turn == chess.BLACK)
        move, info = engine_search.search_with_info(
            board, MAX_DEPTH, engine_is_black=engine_is_black
        )

        if move is None:
            print("Engine returned no move — game over?")
            break

        san = board.san(move)
        move_num = board.fullmove_number
        side = "W" if board.turn == chess.WHITE else "B"
        board.push(move)
        move_count += 1

        # Print move info
        eval_cp = info.get("eval_cp", "?")
        depth = info.get("depth", "?")
        nodes = info.get("nodes", "?")
        time_ms = info.get("time_ms", "?")
        check = "+" if board.is_check() else ""
        if board.is_checkmate():
            check = "#"

        print(f"  {move_num:>3}. {side} {san}{check:<4}  "
              f"eval={eval_cp:>7} cp  d={depth}  "
              f"nodes={nodes}  time={time_ms}ms")

        if board.is_checkmate():
            print(f"\n{'='*62}")
            print(f"  ✓ CHECKMATE in {move_count} half-moves!")
            print(f"{'='*62}")
            print(f"\n{board}\n")
            return

    # Game ended without checkmate
    print(f"\n{board}\n")
    if board.is_stalemate():
        print("  ✗ STALEMATE — engine failed to avoid stalemate!")
    elif board.is_insufficient_material():
        print("  ✗ Draw — insufficient material (should not happen in KBN).")
    elif board.is_seventyfive_moves():
        print("  ✗ Draw — 75-move rule.")
    elif move_count >= max_moves:
        print(f"  ✗ No checkmate within {max_moves} half-moves.")
    else:
        print(f"  Result: {board.result()}")


if __name__ == "__main__":
    main()
