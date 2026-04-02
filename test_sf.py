import os
from stockfish import Stockfish
sf_path = r"c:\Users\Gokul\Desktop\IT255_AIproj\data\stockfish\stockfish-windows-x86-64-avx2.exe"
if not os.path.exists(sf_path):
    sf_path = r"c:\Users\Gokul\Desktop\IT255_AIproj\data\stockfish\stockfish.exe"

sf = Stockfish(sf_path)

# White is up a queen
sf.set_fen_position("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/1NBQKBNR w KQkq - 0 1")
print("White down queen, White to move:", sf.get_evaluation())

sf.set_fen_position("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/1NBQKBNR b KQkq - 0 1")
print("White down queen, Black to move:", sf.get_evaluation())
