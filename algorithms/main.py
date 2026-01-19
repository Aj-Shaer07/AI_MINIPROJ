#pip install python-chess

import chess
from search import iterative_deepening

board = chess.Board()
MAX_DEPTH = 4

while not board.is_game_over():
    print(board, "\n")

    if board.turn == chess.WHITE:
        move = input("Your move (SAN): ")
        board.push_san(move)
    else:
        engine_move = iterative_deepening(board, MAX_DEPTH, engine_is_black=True)
        board.push(engine_move)
        print("Engine plays:", engine_move)

print("Game Over:", board.result())
