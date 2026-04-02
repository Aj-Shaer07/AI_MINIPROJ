"""
Pygame Self-Play Viewer: Tuned vs Original
==========================================
Launches a pygame window showing self-play games in real-time.
Properly swaps ALL 784 parameters between engines.

Usage:
    python algorithms/selfplay_viewer.py --games 5 --depth 4
"""

import os
import sys
import time
import threading
import argparse

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "UI"))

import chess
import pygame

from algorithms.search import iterative_deepening
from algorithms.transposition import clear as tt_clear
import algorithms.evaluation as ev

# ── Colors ──
BG_COLOR        = (30, 30, 40)
LIGHT_SQ        = (240, 217, 181)
DARK_SQ         = (181, 136, 99)
HIGHLIGHT_FROM  = (186, 202, 68, 160)
HIGHLIGHT_TO    = (246, 246, 105, 160)
TEXT_COLOR       = (220, 220, 220)
ACCENT_TUNED    = (0, 210, 255)
ACCENT_ORIG     = (255, 107, 107)
PANEL_BG        = (40, 40, 55)

# ── Piece Unicode ──
PIECE_UNICODE = {
    (chess.PAWN, chess.WHITE): '♙', (chess.KNIGHT, chess.WHITE): '♘',
    (chess.BISHOP, chess.WHITE): '♗', (chess.ROOK, chess.WHITE): '♖',
    (chess.QUEEN, chess.WHITE): '♕', (chess.KING, chess.WHITE): '♔',
    (chess.PAWN, chess.BLACK): '♟', (chess.KNIGHT, chess.BLACK): '♞',
    (chess.BISHOP, chess.BLACK): '♝', (chess.ROOK, chess.BLACK): '♜',
    (chess.QUEEN, chess.BLACK): '♛', (chess.KING, chess.BLACK): '♚',
}

# ── PST names ──
PST_TABLE_NAMES = [
    "MG_PAWN_TABLE", "EG_PAWN_TABLE", "MG_KNIGHT_TABLE", "EG_KNIGHT_TABLE",
    "MG_BISHOP_TABLE", "EG_BISHOP_TABLE", "MG_ROOK_TABLE", "EG_ROOK_TABLE",
    "MG_QUEEN_TABLE", "EG_QUEEN_TABLE", "MG_KING_TABLE", "EG_KING_TABLE",
]
BONUS_NAMES = [
    "DOUBLED_PAWN_PENALTY", "ISOLATED_PAWN_PENALTY", "BISHOP_PAIR_BONUS",
    "ROOK_OPEN_FILE_BONUS", "ROOK_SEMI_OPEN_FILE_BONUS", "KING_SHIELD_BONUS",
]

def _flip(table):
    result = []
    for rank in range(7, -1, -1):
        result.extend(table[rank * 8 : rank * 8 + 8])
    return result


def snapshot_weights():
    snap = {"MG_VALUE": dict(ev.MG_VALUE), "EG_VALUE": dict(ev.EG_VALUE)}
    for name in PST_TABLE_NAMES:
        snap[name] = list(getattr(ev, name))
    for name in BONUS_NAMES:
        snap[name] = getattr(ev, name)
    return snap


def apply_weights(snap):
    ev.MG_VALUE.update(snap["MG_VALUE"])
    ev.EG_VALUE.update(snap["EG_VALUE"])
    for name in PST_TABLE_NAMES:
        table = getattr(ev, name)
        for i in range(64):
            table[i] = snap[name][i]
    for name in BONUS_NAMES:
        setattr(ev, name, snap[name])
    ev.MG_PST = {
        chess.PAWN: ev.MG_PAWN_TABLE, chess.KNIGHT: ev.MG_KNIGHT_TABLE,
        chess.BISHOP: ev.MG_BISHOP_TABLE, chess.ROOK: ev.MG_ROOK_TABLE,
        chess.QUEEN: ev.MG_QUEEN_TABLE, chess.KING: ev.MG_KING_TABLE,
    }
    ev.EG_PST = {
        chess.PAWN: ev.EG_PAWN_TABLE, chess.KNIGHT: ev.EG_KNIGHT_TABLE,
        chess.BISHOP: ev.EG_BISHOP_TABLE, chess.ROOK: ev.EG_ROOK_TABLE,
        chess.QUEEN: ev.EG_QUEEN_TABLE, chess.KING: ev.EG_KING_TABLE,
    }


# Capture tuned weights
TUNED_SNAP = snapshot_weights()

# Build original weights
ORIG_SNAP = {
    "MG_VALUE": {chess.PAWN: 82, chess.KNIGHT: 337, chess.BISHOP: 365,
                 chess.ROOK: 477, chess.QUEEN: 1025, chess.KING: 0},
    "EG_VALUE": {chess.PAWN: 94, chess.KNIGHT: 281, chess.BISHOP: 297,
                 chess.ROOK: 512, chess.QUEEN: 936, chess.KING: 0},
    "DOUBLED_PAWN_PENALTY": -15, "ISOLATED_PAWN_PENALTY": -20,
    "BISHOP_PAIR_BONUS": 30, "ROOK_OPEN_FILE_BONUS": 25,
    "ROOK_SEMI_OPEN_FILE_BONUS": 12, "KING_SHIELD_BONUS": 10,
}
# Original PeSTO PSTs
_pst_data = {
    "MG_PAWN_TABLE": [0,0,0,0,0,0,0,0,98,134,61,95,68,126,34,-11,-6,7,26,31,65,56,25,-20,-14,13,6,21,23,12,17,-23,-27,-2,-5,12,17,6,10,-25,-26,-4,-4,-10,3,3,33,-12,-35,-1,-20,-23,-15,24,38,-22,0,0,0,0,0,0,0,0],
    "EG_PAWN_TABLE": [0,0,0,0,0,0,0,0,178,173,158,134,147,132,165,187,94,100,85,67,56,53,82,84,32,24,13,5,-2,4,17,17,13,9,-3,-7,-7,-8,3,-1,4,7,-6,1,0,-5,-1,-8,13,8,8,10,13,0,2,-7,0,0,0,0,0,0,0,0],
    "MG_KNIGHT_TABLE": [-167,-89,-34,-49,61,-97,-15,-107,-73,-41,72,36,23,62,7,-17,-47,60,37,65,84,129,73,44,-9,17,19,53,37,69,18,22,-13,4,16,13,28,19,21,-8,-23,-9,12,10,19,17,25,-16,-29,-53,-12,-3,-1,18,-14,-19,-105,-21,-58,-33,-17,-28,-19,-23],
    "EG_KNIGHT_TABLE": [-58,-38,-13,-28,-31,-27,-63,-99,-25,-8,-25,-2,-9,-25,-24,-52,-24,-20,10,9,-1,-9,-19,-41,-17,3,22,22,22,11,8,-18,-18,-6,16,25,16,17,4,-18,-23,-3,-1,15,10,-3,-20,-22,-42,-20,-10,-5,-2,-20,-23,-44,-29,-51,-23,-15,-22,-18,-50,-64],
    "MG_BISHOP_TABLE": [-29,4,-82,-37,-25,-42,7,-8,-26,16,-18,-13,30,59,18,-47,-16,37,43,40,35,50,37,-2,-4,5,19,50,37,37,7,-2,-6,13,13,26,34,12,10,4,0,15,15,15,14,27,18,10,4,15,16,0,7,21,33,1,-33,-3,-14,-21,-13,-12,-39,-21],
    "EG_BISHOP_TABLE": [-14,-21,-11,-8,-7,-9,-17,-24,-8,-4,7,-12,-3,-13,-4,-14,2,-8,0,-1,-2,6,0,4,-3,9,12,9,14,10,3,2,-6,3,13,19,7,10,-3,-9,-12,-3,8,10,13,3,-7,-15,-14,-18,-7,-1,4,-9,-15,-27,-23,-9,-23,-5,-9,-16,-5,-17],
    "MG_ROOK_TABLE": [32,42,32,51,63,9,31,43,27,32,58,62,80,67,26,44,-5,19,26,36,17,45,61,16,-24,-11,7,26,24,35,-8,-20,-36,-26,-12,-1,9,-7,6,-23,-45,-25,-16,-17,3,0,-5,-33,-44,-16,-20,-9,-1,11,-6,-71,-19,-13,1,17,16,7,-37,-26],
    "EG_ROOK_TABLE": [13,10,18,15,12,12,8,5,11,13,13,11,-3,3,8,3,7,7,7,5,4,-3,-5,-3,4,3,13,1,2,1,-1,2,3,5,8,4,-5,-6,-8,-11,-4,0,-5,-1,-7,-12,-8,-16,-6,-6,0,2,-9,-9,-11,-3,-9,2,3,-1,-5,-13,4,-20],
    "MG_QUEEN_TABLE": [-28,0,29,12,59,44,43,45,-24,-39,-5,1,-16,57,28,54,-13,-17,7,8,29,56,47,57,-27,-27,-16,-16,-1,17,-2,1,-9,-26,-9,-10,-2,-4,3,-3,-14,2,-11,-2,-5,2,14,5,-35,-8,11,2,8,15,-3,1,-1,-18,-9,10,-15,-25,-31,-50],
    "EG_QUEEN_TABLE": [-9,22,22,27,27,19,10,20,-17,20,32,41,58,25,30,0,-20,6,9,49,47,35,19,9,3,22,24,45,57,40,57,36,-18,28,19,47,31,34,39,23,-16,-27,15,6,9,17,10,5,-22,-23,-30,-16,-16,-23,-36,-32,-33,-28,-22,-43,-5,-32,-20,-41],
    "MG_KING_TABLE": [-65,23,16,-15,-56,-34,2,13,29,-1,-20,-7,-8,-4,-38,-29,-9,24,2,-16,-20,6,22,-22,-17,-20,-12,-27,-30,-25,-14,-36,-49,-1,-27,-39,-46,-44,-33,-51,-14,-14,-22,-46,-44,-30,-15,-27,1,7,-8,-64,-43,-16,9,8,-15,36,12,-54,8,-28,24,14],
    "EG_KING_TABLE": [-74,-35,-18,-18,-11,15,4,-17,-12,17,14,17,17,38,23,11,10,17,23,15,20,45,44,13,-8,22,24,27,26,33,26,3,-18,-4,21,24,27,23,9,-11,-19,-3,11,21,23,16,7,-9,-27,-11,4,13,14,4,-5,-17,-53,-34,-21,-11,-28,-14,-24,-43],
}
for name, data in _pst_data.items():
    ORIG_SNAP[name] = _flip(data)


# ── Shared game state ──
class GameState:
    def __init__(self):
        self.board = chess.Board()
        self.game_num = 0
        self.total_games = 0
        self.tuned_color = "White"
        self.last_move = None
        self.last_san = ""
        self.last_engine = ""
        self.last_eval = 0
        self.move_list = []
        self.tuned_score = 0.0
        self.orig_score = 0.0
        self.status = "Starting..."
        self.results = []
        self.done = False
        self.lock = threading.Lock()


def engine_thread(state, depth, num_games):
    """Run self-play games in the background."""
    state.total_games = num_games

    for game_num in range(1, num_games + 1):
        tuned_is_white = (game_num % 2 == 1)

        with state.lock:
            state.board = chess.Board()
            state.game_num = game_num
            state.tuned_color = "White" if tuned_is_white else "Black"
            state.last_move = None
            state.move_list = []
            state.status = f"Game {game_num}/{num_games} — Playing..."

        tt_clear()
        move_count = 0

        while not state.board.is_game_over() and move_count < 200:
            is_white = state.board.turn == chess.WHITE
            use_tuned = (is_white == tuned_is_white)

            if use_tuned:
                apply_weights(TUNED_SNAP)
                label = "TUNED"
            else:
                apply_weights(ORIG_SNAP)
                label = "ORIG"

            tt_clear()
            move, value, d, stats, elapsed = iterative_deepening(state.board, depth)

            if move is None:
                break

            san = state.board.san(move)

            with state.lock:
                state.board.push(move)
                state.last_move = move
                state.last_san = san
                state.last_engine = label
                state.last_eval = value
                state.move_list.append(f"{san}[{label}]")

            move_count += 1
            time.sleep(1.0)  # 1s delay so moves are visible

        # Determine result
        result = state.board.result()
        if result == "1-0":
            score = 1.0 if tuned_is_white else 0.0
        elif result == "0-1":
            score = 0.0 if tuned_is_white else 1.0
        else:
            score = 0.5

        with state.lock:
            state.tuned_score += score
            state.orig_score += (1.0 - score)
            if score == 1.0:
                state.results.append("TUNED WINS")
            elif score == 0.0:
                state.results.append("ORIG WINS")
            else:
                state.results.append("DRAW")
            state.status = f"Game {game_num} done: {state.results[-1]}"

        time.sleep(2)  # pause between games

    with state.lock:
        state.done = True
        state.status = "All games complete!"

    apply_weights(TUNED_SNAP)


def draw_board(screen, board, sq_size, offset_x, offset_y, last_move, piece_font):
    """Draw the chess board with pieces."""
    for rank in range(8):
        for file in range(8):
            x = offset_x + file * sq_size
            y = offset_y + (7 - rank) * sq_size
            is_light = (rank + file) % 2 == 0
            color = LIGHT_SQ if is_light else DARK_SQ

            # Highlight last move
            sq = chess.square(file, rank)
            if last_move and (sq == last_move.from_square or sq == last_move.to_square):
                color = (186, 202, 68) if sq == last_move.from_square else (246, 246, 105)

            pygame.draw.rect(screen, color, (x, y, sq_size, sq_size))

            # Draw piece
            piece = board.piece_at(sq)
            if piece:
                symbol = PIECE_UNICODE.get((piece.piece_type, piece.color), '?')
                text = piece_font.render(symbol, True, (0, 0, 0))
                # Center the piece
                tx = x + (sq_size - text.get_width()) // 2
                ty = y + (sq_size - text.get_height()) // 2
                screen.blit(text, (tx, ty))

    # Draw file and rank labels
    label_font = pygame.font.SysFont("Arial", 14)
    for file in range(8):
        lbl = label_font.render(chr(ord('a') + file), True, TEXT_COLOR)
        screen.blit(lbl, (offset_x + file * sq_size + sq_size // 2 - 4,
                          offset_y + 8 * sq_size + 4))
    for rank in range(8):
        lbl = label_font.render(str(rank + 1), True, TEXT_COLOR)
        screen.blit(lbl, (offset_x - 16, offset_y + (7 - rank) * sq_size + sq_size // 2 - 7))


def draw_panel(screen, state, panel_x, panel_y, panel_w, panel_h, small_font, title_font):
    """Draw the info panel on the right side."""
    # Panel background
    pygame.draw.rect(screen, PANEL_BG, (panel_x, panel_y, panel_w, panel_h), border_radius=10)

    y = panel_y + 15
    # Title
    t = title_font.render("Self-Play Benchmark", True, ACCENT_TUNED)
    screen.blit(t, (panel_x + 15, y)); y += 35

    # Scoreboard
    t = small_font.render(f"Game {state.game_num}/{state.total_games}", True, TEXT_COLOR)
    screen.blit(t, (panel_x + 15, y)); y += 22

    t = small_font.render(f"Tuned ({state.tuned_color}):", True, ACCENT_TUNED)
    screen.blit(t, (panel_x + 15, y))
    t = small_font.render(f"{state.tuned_score:.1f}", True, ACCENT_TUNED)
    screen.blit(t, (panel_x + 170, y)); y += 22

    orig_color = "Black" if state.tuned_color == "White" else "White"
    t = small_font.render(f"Original ({orig_color}):", True, ACCENT_ORIG)
    screen.blit(t, (panel_x + 15, y))
    t = small_font.render(f"{state.orig_score:.1f}", True, ACCENT_ORIG)
    screen.blit(t, (panel_x + 170, y)); y += 30

    # Status
    t = small_font.render(state.status, True, (180, 180, 180))
    screen.blit(t, (panel_x + 15, y)); y += 25

    # Last move info
    if state.last_san:
        color = ACCENT_TUNED if state.last_engine == "TUNED" else ACCENT_ORIG
        t = small_font.render(f"Last: {state.last_san} [{state.last_engine}] eval={state.last_eval:+}", True, color)
        screen.blit(t, (panel_x + 15, y))
    y += 30

    # Move list
    t = small_font.render("─── Moves ───", True, (120, 120, 120))
    screen.blit(t, (panel_x + 15, y)); y += 20

    # Show last ~16 moves
    moves = state.move_list[-16:]
    for i, m in enumerate(moves):
        idx = len(state.move_list) - len(moves) + i
        move_num = idx // 2 + 1
        prefix = f"{move_num}." if idx % 2 == 0 else "   "
        color = ACCENT_TUNED if "TUNED" in m else ACCENT_ORIG
        display = m.split("[")[0]  # remove [TUNED]/[ORIG] tag
        tag = "[T]" if "TUNED" in m else "[O]"
        t = small_font.render(f"{prefix} {display} {tag}", True, color)
        screen.blit(t, (panel_x + 15, y)); y += 18
        if y > panel_y + panel_h - 60:
            break

    # Results log
    if state.results:
        y = panel_y + panel_h - 20 * len(state.results) - 30
        t = small_font.render("─── Results ───", True, (120, 120, 120))
        screen.blit(t, (panel_x + 15, y)); y += 20
        for i, r in enumerate(state.results):
            color = ACCENT_TUNED if "TUNED" in r else (ACCENT_ORIG if "ORIG" in r else (255, 217, 61))
            t = small_font.render(f"  G{i+1}: {r}", True, color)
            screen.blit(t, (panel_x + 15, y)); y += 18


def main():
    parser = argparse.ArgumentParser(description="Pygame Self-Play Viewer")
    parser.add_argument("--games", type=int, default=5)
    parser.add_argument("--depth", type=int, default=4)
    args = parser.parse_args()

    pygame.init()
    SQ_SIZE = 65
    BOARD_PX = SQ_SIZE * 8
    PANEL_W = 280
    WIN_W = 40 + BOARD_PX + 20 + PANEL_W + 20
    WIN_H = 40 + BOARD_PX + 40

    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Self-Play: Tuned vs Original")

    # Fonts
    piece_font = pygame.font.SysFont("Segoe UI Symbol", SQ_SIZE - 8)
    small_font = pygame.font.SysFont("Consolas", 14)
    title_font = pygame.font.SysFont("Arial", 20, bold=True)

    clock = pygame.time.Clock()
    state = GameState()

    # Start engine thread
    thread = threading.Thread(target=engine_thread, args=(state, args.depth, args.games), daemon=True)
    thread.start()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        screen.fill(BG_COLOR)

        # Snapshot everything atomically
        with state.lock:
            board_copy = state.board.copy()
            last_move = state.last_move
            # Draw both board and panel inside one lock to stay in sync
            draw_board(screen, board_copy, SQ_SIZE, 30, 30, last_move, piece_font)
            draw_panel(screen, state, 30 + BOARD_PX + 20, 30, PANEL_W, BOARD_PX, small_font, title_font)

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
