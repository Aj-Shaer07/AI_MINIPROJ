# pip install python-chess

import chess
import algorithms.search as engine_search
from typing import Optional

MAX_DEPTH = 6


def print_terminal(board: chess.Board, last_move_san: Optional[str] = None) -> None:
    """Print a compact, human-friendly terminal view of `board`."""
    sep = "=" * 60
    print(sep)
    print(board)

    if last_move_san:
        try:
            move_no = (len(board.move_stack) + 1) // 2
            side = "Black" if board.turn == chess.WHITE else "White"
            print(f"Last move: {last_move_san} — {side} (move {move_no})")
        except Exception:
            print(f"Last move: {last_move_san}")

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
    last_move_san = None
    # Let the user choose their color. Engine will play the opposite.
    choice = input("Choose your color — enter 'w' for White or 'b' for Black (default w): ").strip().lower()
    if choice == 'b':
        player_color = chess.BLACK
    else:
        player_color = chess.WHITE

    while not board.is_game_over():
        print_terminal(board, last_move_san)

        # If it's the player's turn, ask for input; otherwise engine moves.
        if board.turn == player_color:
            move = input("Your move (SAN): ")
            board.push_san(move)
            last_move_san = move
        else:
            # Engine plays the opposite color of the player
            engine_is_black = (player_color == chess.WHITE)
            move, info = engine_search.search_with_info(
                board,
                MAX_DEPTH,
                engine_is_black=engine_is_black
            )

            if move:
                san = board.san(move)
                board.push(move)
                last_move_san = san

                print(f"Engine plays: {san} ({move})")
                print(engine_search.format_search_info(info))

    print("Game Over:", board.result())


if __name__ == "__main__":
    main()
