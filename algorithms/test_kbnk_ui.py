"""
Launch the chess UI starting from a K+B+N vs K position.
Engine has King + Bishop + Knight (Black), you play as the lone King (White) in the center.
Try to survive — can the engine checkmate you?

Run:  python algorithms\\test_kbnk_ui.py
"""
import sys, os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ui_dir = os.path.join(project_root, "UI")
sys.path.insert(0, project_root)
sys.path.insert(0, ui_dir)
os.chdir(ui_dir)

from main import main

# Engine (Black) has K on e8, Bishop on c8, Knight on g8
# You (White) have K on e4 (center)
FEN = "2b1k1n1/8/8/8/4K3/8/8/8 w - - 0 1"

main(human_color="white", fen=FEN)
