import sys
import os
import chess
from typing import Tuple, Optional

# Ensure repository root is importable when this module is loaded from UI/
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Ensure algorithms/ directory is on path so relative imports within algorithms/ work
ALGORITHMS_DIR = os.path.join(ROOT, 'algorithms')
if ALGORITHMS_DIR not in sys.path:
    sys.path.insert(0, ALGORITHMS_DIR)

import algorithms.search as engine_search
import values
import algorithms.main as alg_main


class GameController:
    def __init__(self, max_depth: int = 4, engine_is_black: bool = True):
        self.board = chess.Board()
        self.max_depth = max_depth
        self.engine_is_black = engine_is_black

    def coords_to_square_name(self, r: int, c: int, rows: int = 8) -> str:
        file = chr(ord('a') + int(c))
        rank = str(rows - int(r))
        return f"{file}{rank}"

    def try_player_move(self, from_r: int, from_c: int, to_r: int, to_c: int) -> Tuple[bool, Optional[chess.Move]]:
        from_sq = self.coords_to_square_name(from_r, from_c)
        to_sq = self.coords_to_square_name(to_r, to_c)
        uci = from_sq + to_sq

        # try simple UCI first
        move = None
        try:
            move = chess.Move.from_uci(uci)
        except Exception:
            move = None

        if move and move in self.board.legal_moves:
            try:
                san = self.board.san(move)
            except Exception:
                san = None
            self.board.push(move)
            self.last_move = move
            self.last_move_san = san
            return True, move

        # handle pawn promotion (try common promotions)
        for promo in ['q', 'r', 'b', 'n']:
            try:
                move2 = chess.Move.from_uci(uci + promo)
            except Exception:
                continue
            if move2 in self.board.legal_moves:
                try:
                    san2 = self.board.san(move2)
                except Exception:
                    san2 = None
                self.board.push(move2)
                self.last_move = move2
                self.last_move_san = san2
                return True, move2

        return False, None

    def engine_move(self):
        if self.board.is_game_over():
            return None
        move = engine_search.iterative_deepening(self.board, self.max_depth, engine_is_black=self.engine_is_black)
        if move is None:
            return None
        try:
            san = self.board.san(move)
        except Exception:
            san = None
        self.board.push(move)
        self.last_move = move
        self.last_move_san = san
        return move

    def sync_to_ui(self, ui_board) -> None:
        """Populate `ui_board` (an instance of UI.chessboard.ChessBoard) from the current chess.Board."""
        # Faster incremental sync to reduce UI lag:
        #  - iterate current board piece_map once and update UI slots directly
        #  - mark visited positions then clear any UI squares not visited
        rows = ui_board.rows
        cols = ui_board.cols
        board_map = self.board.piece_map()
        ui_grid = ui_board.board
        set_piece = ui_board.set_piece
        sym_map = values.PIECE_SYMBOL_MAP
        visited = set()

        # update or set pieces present on the chess.Board
        for sq, piece in board_map.items():
            file_idx = chess.square_file(sq)
            rank_idx = chess.square_rank(sq)
            col = file_idx
            row = rows - 1 - rank_idx
            visited.add((row, col))
            color_key = 'white' if piece.color == chess.WHITE else 'black'
            symbol = sym_map[piece.piece_type][0 if piece.color == chess.BLACK else 1]
            desired_piece = (symbol, color_key)
            # only update when different to avoid unnecessary redraw work
            if ui_grid[row][col] != desired_piece:
                set_piece(row, col, desired_piece)

        # clear any UI squares that are not part of current board state
        for r in range(rows):
            for c in range(cols):
                if ui_grid[r][c] is not None and (r, c) not in visited:
                    set_piece(r, c, None)

    def print_terminal(self):
        # Delegate terminal printing to algorithms.main.print_terminal for consistent formatting
        alg_main.print_terminal(self.board, getattr(self, 'last_move_san', None))
