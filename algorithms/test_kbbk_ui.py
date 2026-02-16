"""
Launch the chess UI starting from a K+B+B vs K position.
Engine has King + 2 Bishops (Black), you play as the lone King (White) in the center.
Try to survive — can the engine checkmate you?

Run:  python algorithms\\test_kbbk_ui.py
"""
import sys, os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ui_dir = os.path.join(project_root, "UI")
sys.path.insert(0, project_root)
sys.path.insert(0, ui_dir)
os.chdir(ui_dir)

from main import main

# Engine (Black) has K on e8, Bishops on c8 and f8 (opposite colors)
# You (White) have K on e4 (center)
FEN = "2b1kb2/8/8/8/4K3/8/8/8 w - - 0 1"

main(human_color="white", fen=FEN)
