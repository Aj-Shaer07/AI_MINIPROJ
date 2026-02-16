"""
Automated test suite for the chess engine.
Run:  python test_engine.py
"""

import sys
import time
import random

import chess

# Local imports
from search import search_with_info, format_search_info
from transposition import clear as tt_clear


# ─────────────────────────────────────────────────────────
# 1.  TACTICAL PUZZLE TESTS
# ─────────────────────────────────────────────────────────
PUZZLES = [
    {
        "name": "Back-rank mate",
        "fen": "6k1/5ppp/8/8/8/8/8/R3K3 w Q - 0 1",
        "best": ["a1a8"],  # Ra8#
        "depth": 4,
    },
    {
        "name": "Knight fork winning queen",
        "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1",
        "best": ["h5f7"],  # Qxf7#  (or winning)
        "depth": 4,
    },
    {
        "name": "Queen sacrifice mate (Légal's Mate pattern)",
        "fen": "r2qkbnr/ppp2ppp/2np4/4p3/2B1P1b1/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1",
        "best": ["f3e5", "d1d4", "c4f7"],  # any winning move accepted
        "depth": 4,
    },
    {
        "name": "Promotion tactic",
        "fen": "8/P7/8/8/8/8/8/4K2k w - - 0 1",
        "best": ["a7a8q", "a7a8r", "a7a8n", "a7a8b"],  # any promotion wins
        "depth": 4,
    },
    {
        "name": "Simple capture wins material",
        "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        "best": None,  # just check it returns a legal move
        "depth": 4,
    },
]


def test_puzzles():
    print("=" * 60)
    print("TACTICAL PUZZLE TESTS")
    print("=" * 60)
    passed = 0
    total = len(PUZZLES)

    for puzzle in PUZZLES:
        tt_clear()
        board = chess.Board(puzzle["fen"])
        move, info = search_with_info(board, puzzle["depth"], engine_is_black=(board.turn == chess.BLACK))

        move_uci = move.uci() if move else "None"
        is_legal = move in board.legal_moves if move else False

        if puzzle["best"] is None:
            # Just check it returns a legal move
            ok = is_legal
        else:
            ok = move_uci in puzzle["best"] and is_legal

        status = "PASS" if ok else "FAIL"
        print(f"\n  [{status}] {puzzle['name']}")
        print(f"    FEN:      {puzzle['fen']}")
        print(f"    Expected: {puzzle['best']}")
        print(f"    Got:      {move_uci}")
        print(f"    {format_search_info(info)}")

        if ok:
            passed += 1

    print(f"\nPuzzle results: {passed}/{total} passed")
    return passed, total


# ─────────────────────────────────────────────────────────
# 2.  SELF-PLAY: ENGINE VS RANDOM
# ─────────────────────────────────────────────────────────
def test_self_play(num_games=3, max_moves=150, engine_depth=3):
    print("\n" + "=" * 60)
    print(f"SELF-PLAY: ENGINE (Black) vs RANDOM (White) — {num_games} games")
    print("=" * 60)

    wins = 0
    for g in range(num_games):
        tt_clear()
        board = chess.Board()
        move_count = 0

        while not board.is_game_over() and move_count < max_moves:
            if board.turn == chess.WHITE:
                # Random mover
                moves = list(board.legal_moves)
                board.push(random.choice(moves))
            else:
                # Engine
                move, info = search_with_info(board, engine_depth, engine_is_black=True)
                if move and move in board.legal_moves:
                    board.push(move)
                else:
                    break
            move_count += 1

        result = board.result()
        won = result == "0-1"
        status = "WIN" if won else ("DRAW" if "1/2" in result else "LOSS")
        print(f"  Game {g + 1}: {result} ({status}) in {move_count} moves")
        if won:
            wins += 1

    print(f"\nSelf-play results: {wins}/{num_games} wins")
    return wins, num_games


# ─────────────────────────────────────────────────────────
# 3.  REGRESSION: START-POSITION SEARCH
# ─────────────────────────────────────────────────────────
def test_regression():
    print("\n" + "=" * 60)
    print("REGRESSION: Starting position depth-4 search")
    print("=" * 60)

    tt_clear()
    board = chess.Board()
    t0 = time.time()
    move, info = search_with_info(board, 4, engine_is_black=False)
    elapsed = time.time() - t0

    is_legal = move in board.legal_moves if move else False
    under_time = elapsed < 30.0

    print(f"  Move:    {move.uci() if move else 'None'}")
    print(f"  Legal:   {is_legal}")
    print(f"  Time:    {elapsed:.2f}s (limit: 30s)")
    print(f"  {format_search_info(info)}")

    ok = is_legal and under_time
    status = "PASS" if ok else "FAIL"
    print(f"  Result:  [{status}]")
    return ok


# ─────────────────────────────────────────────────────────
# 4.  ENDGAME CONVERSION TESTS
# ─────────────────────────────────────────────────────────
ENDGAME_POSITIONS = [
    {
        "name": "K+Q vs K",
        "fen": "8/8/8/8/3k4/8/8/4K2Q w - - 0 1",
        "max_moves": 30,
        "description": "Must deliver checkmate",
    },
    {
        "name": "K+R vs K",
        "fen": "8/8/8/8/3k4/8/8/R3K3 w - - 0 1",
        "max_moves": 50,
        "description": "Must deliver checkmate",
    },
    {
        "name": "K+R+3P vs K+R (winning rook endgame)",
        "fen": "8/8/8/8/3k4/8/PPP5/R3K3 w Q - 0 1",
        "max_moves": 80,
        "description": "Must win or achieve decisive advantage",
    },
]


def test_endgames():
    print("\n" + "=" * 60)
    print("ENDGAME CONVERSION TESTS")
    print("=" * 60)
    passed = 0
    total = len(ENDGAME_POSITIONS)

    for eg in ENDGAME_POSITIONS:
        tt_clear()
        board = chess.Board(eg["fen"])
        move_count = 0
        max_moves = eg["max_moves"]

        # Play out the endgame: engine plays both sides but from
        # a winning position for White. Engine should convert.
        while not board.is_game_over() and move_count < max_moves:
            move, info = search_with_info(board, 5, engine_is_black=(board.turn == chess.BLACK))
            if move and move in board.legal_moves:
                board.push(move)
            else:
                break
            move_count += 1

        result = board.result()
        is_checkmate = board.is_checkmate()
        is_stalemate = board.is_stalemate()

        # Check success: either checkmate by White, or decisive advantage
        if is_checkmate and board.turn == chess.BLACK:
            ok = True
            outcome = "CHECKMATE"
        elif result == "1-0":
            ok = True
            outcome = "WIN"
        elif is_stalemate or result == "1/2-1/2":
            ok = False
            outcome = "STALEMATE/DRAW"
        elif move_count >= max_moves:
            # Check if we at least have a very strong position
            ok = False
            outcome = f"TIMEOUT ({move_count} moves)"
        else:
            ok = False
            outcome = f"UNKNOWN ({result})"

        status = "PASS" if ok else "FAIL"
        print(f"\n  [{status}] {eg['name']}")
        print(f"    FEN:       {eg['fen']}")
        print(f"    Outcome:   {outcome} in {move_count} moves")
        print(f"    Expected:  {eg['description']}")

        if ok:
            passed += 1

    print(f"\nEndgame results: {passed}/{total} passed")
    return passed, total


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    random.seed(42)

    p_passed, p_total = test_puzzles()
    w_wins, w_total = test_self_play()
    r_ok = test_regression()
    e_passed, e_total = test_endgames()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Puzzles:    {p_passed}/{p_total}")
    print(f"  Self-play:  {w_wins}/{w_total} wins")
    print(f"  Regression: {'PASS' if r_ok else 'FAIL'}")
    print(f"  Endgames:   {e_passed}/{e_total}")

    all_pass = p_passed >= 3 and w_wins >= 2 and r_ok and e_passed >= 2
    print(f"\n  Overall: {'ALL PASS' if all_pass else 'SOME FAILURES'}")

    sys.exit(0 if all_pass else 1)

