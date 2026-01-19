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
import pieces as ui_pieces


PIECE_TYPE_MAP = {
    chess.PAWN: 'pawn',
    chess.KNIGHT: 'knight',
    chess.BISHOP: 'bishop',
    chess.ROOK: 'rook',
    chess.QUEEN: 'queen',
    chess.KING: 'king',
}


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
            self.board.push(move)
            return True, move

        # handle pawn promotion (try common promotions)
        for promo in ['q', 'r', 'b', 'n']:
            try:
                move2 = chess.Move.from_uci(uci + promo)
            except Exception:
                continue
            if move2 in self.board.legal_moves:
                self.board.push(move2)
                return True, move2

        return False, None

    def engine_move(self):
        if self.board.is_game_over():
            return None
        move = engine_search.iterative_deepening(self.board, self.max_depth, engine_is_black=self.engine_is_black)
        if move is None:
            return None
        self.board.push(move)
        return move

    def sync_to_ui(self, ui_board) -> None:
        """Populate `ui_board` (an instance of UI.chessboard.ChessBoard) from the current chess.Board."""
        ui_board.clear()
        rows = ui_board.rows
        for sq, piece in self.board.piece_map().items():
            file_idx = chess.square_file(sq)
            rank_idx = chess.square_rank(sq)
            col = file_idx
            row = rows - 1 - rank_idx

            piece_name = PIECE_TYPE_MAP.get(piece.piece_type, None)
            color_key = 'white' if piece.color == chess.WHITE else 'black'
            symbol = ui_pieces.get(piece_name, color_key)
            ui_board.set_piece(row, col, (symbol, color_key))

    def print_terminal(self):
        print(self.board)
        if self.board.is_checkmate():
            print("Game Over: checkmate; result:", self.board.result())
        elif self.board.is_stalemate():
            print("Game Over: stalemate; result:", self.board.result())
        elif self.board.is_insufficient_material():
            print("Game Over: insufficient material; result:", self.board.result())
        elif self.board.is_seventyfive_moves() or self.board.is_fivefold_repetition():
            print("Game Over: draw by rule; result:", self.board.result())
        else:
            if self.board.is_check():
                print("Check to", "white" if self.board.turn == chess.WHITE else "black")
