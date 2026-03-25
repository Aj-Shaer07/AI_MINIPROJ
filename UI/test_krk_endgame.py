"""
Manual UI Test: KBB vs K and KBN vs K endgame conversion
========================================================
Launches the full pygame chess UI with an endgame position so you can
manually test whether the engine can convert the win.

You play the lone Black King. The engine plays White with the winning pieces.

Usage:
    python UI/test_krk_endgame.py                     # default KBN position
    python UI/test_krk_endgame.py --type kbb          # test KBB instead
    python UI/test_krk_endgame.py --preset corner     # test corner preset
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

# ── preset positions ──────────────────────────────────────────────────
PRESETS_KBB = {
    "default": "8/8/8/3k4/8/8/8/2B1KB2 w - - 0 1",
    "center":  "8/8/8/3k4/8/8/8/2B1KB2 w - - 0 1",
    "corner":  "k7/8/8/8/8/8/8/2B1KB2 w - - 0 1",
    "edge":    "4k3/8/8/8/8/8/8/2B1KB2 w - - 0 1",
    "close":   "8/8/8/8/3k4/4BB2/3K4/8 w - - 0 1",
}

PRESETS_KBN = {
    "default": "8/8/8/3k4/8/8/8/2N1KB2 w - - 0 1",
    "center":  "8/8/8/3k4/8/8/8/2N1KB2 w - - 0 1",
    "corner":  "k7/8/8/8/8/8/8/2N1KB2 w - - 0 1",
    "edge":    "4k3/8/8/8/8/8/8/2N1KB2 w - - 0 1",
    "close":   "8/8/8/8/3k4/4NB2/3K4/8 w - - 0 1",
}

def main():
    parser = argparse.ArgumentParser(
        description="UI test: can the engine convert KBB or KBN vs K?"
    )
    parser.add_argument(
        "--type", type=str, choices=["kbb", "kbn"], default="kbn",
        help="Which endgame to test (default: kbn)."
    )
    parser.add_argument(
        "--fen", type=str, default=None,
        help="Custom starting FEN."
    )
    parser.add_argument(
        "--preset", type=str, choices=PRESETS_KBB.keys(), default="default",
        help="Use a preset position (default: 'default')."
    )
    args = parser.parse_args()

    presets = PRESETS_KBB if args.type == "kbb" else PRESETS_KBN
    fen = args.fen if args.fen else presets[args.preset]

    print(f"[{args.type.upper()} Test] Starting position: {fen}")
    print(f"[{args.type.upper()} Test] You play Black (lone param King). Engine plays White.")
    print(f"[{args.type.upper()} Test] The engine should be able to force checkmate.\n")

    # Clear sys.argv so the UI main doesn't try to parse our arguments
    sys.argv = [sys.argv[0]]

    # Launch the full pygame UI with this position.
    # human_color='black' → engine plays White (engine_is_black=False)
    import main as ui_main
    ui_main.main(
        start_time=0,       # no clock
        increment=0,
        human_color="black", # you play the lone Black king
        fen=fen,
    )


if __name__ == "__main__":
    main()
