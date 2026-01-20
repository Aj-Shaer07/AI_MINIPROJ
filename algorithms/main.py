# pip install python-chess

import chess
import algorithms.search as engine_search
from typing import Optional

MAX_DEPTH = 4


def print_terminal(board: chess.Board, last_move_san: Optional[str] = None) -> None:
    """Print a compact, human-friendly terminal view of `board`.

    Shows the ASCII board, whose turn it is, and the most recent move
    with move number and which side played it when available.
    """
    sep = "=" * 60
    # Board header
    print(sep)
    print(board)

    # Last move details
    if last_move_san:
        # Determine move number and side from board.move_stack
        try:
            last_move = board.move_stack[-1]
            move_no = (len(board.move_stack) + 1) // 2
            side = 'Black' if board.turn == chess.WHITE else 'White'
            print(f"Last move: {last_move_san} — {side} (move {move_no})")
        except Exception:
            print(f"Last move: {last_move_san}")

    # Turn and state
    print(f"To move: {'White' if board.turn == chess.WHITE else 'Black'}")

    if board.is_checkmate():
        print(f"Result: Checkmate — {board.result()}")
    elif board.is_stalemate():
        print(f"Result: Stalemate — {board.result()}")
    elif board.is_insufficient_material():
        print(f"Result: Insufficient material — {board.result()}")
    elif board.is_seventyfive_moves() or board.is_fivefold_repetition():
        print(f"Result: Draw by rule — {board.result()}")
    else:
        if board.is_check():
            print(f"Check to {'White' if board.turn == chess.WHITE else 'Black'}")

    print(sep)


def main():
    board = chess.Board()
    while not board.is_game_over():
        print_terminal(board)

        if board.turn == chess.WHITE:
            move = input("Your move (SAN): ")
            board.push_san(move)
        else:
            engine_move = engine_search.iterative_deepening(board, MAX_DEPTH, engine_is_black=True)
            if engine_move:
                san = board.san(engine_move)
                board.push(engine_move)
                print(f"Engine plays: {san} ({engine_move})")

    print("Game Over:", board.result())


if __name__ == '__main__':
    main()
