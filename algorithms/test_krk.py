"""
Test: King + Rook vs King endgame
Lets the engine play both sides to see if it can deliver checkmate.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import chess
from algorithms import search

# K+R vs K: White has King e1, Rook a1; Black has King e8
board = chess.Board("4k3/8/8/8/8/8/8/R3K3 w - - 0 1")
print("=" * 50)
print("  K+R vs K  Self-Play Test")
print("=" * 50)
print()
print("Starting position:")
print(board)
print()

move_list = []
for ply in range(120):
    if board.is_game_over():
        break
    move, info = search.search_with_info(
        board, 5, engine_is_black=(board.turn == chess.BLACK)
    )
    if move is None:
        print("Engine returned None!")
        break
    san = board.san(move)
    if board.turn == chess.WHITE:
        move_list.append(f"{board.fullmove_number}. {san}")
    else:
        move_list[-1] += f" {san}"
    board.push(move)

# Print the game
for line in move_list:
    print(line)

print()
if board.is_checkmate():
    winner = "Black" if board.turn == chess.WHITE else "White"
    # actually, if it's Black's turn and checkmate, White delivered it
    # wait — is_checkmate means the side to move is in checkmate
    winner = "White" if board.turn == chess.BLACK else "Black"
    print(f"CHECKMATE! {winner} wins in {board.fullmove_number - 1} moves.")
elif board.is_stalemate():
    print("STALEMATE — draw (engine failed to avoid stalemate!)")
else:
    print(f"Game ended: {board.result()} after {board.fullmove_number} moves")

print()
print("Final position:")
print(board)
