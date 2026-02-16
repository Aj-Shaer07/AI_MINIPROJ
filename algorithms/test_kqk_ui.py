"""
Launch the chess UI starting from a K+Q vs K position.
Engine has King + Queen (Black), you play as the lone King (White).
Try to survive — can the engine checkmate you?

Run:  python algorithms\\test_kqk_ui.py
"""
import sys, os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ui_dir = os.path.join(project_root, "UI")
sys.path.insert(0, project_root)
sys.path.insert(0, ui_dir)
os.chdir(ui_dir)

from main import main

# Engine (Black) has K on e8 + Q on d8
# You (White) have K on e1
FEN = "3qk3/8/8/8/8/8/8/4K3 w - - 0 1"

main(human_color="white", fen=FEN)
