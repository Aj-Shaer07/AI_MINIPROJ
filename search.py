from evaluation import evaluate, MATE_SCORE
from move_generation import generate_legal_moves
from move_ordering import order_moves
from transposition import lookup, store

REPETITION_PENALTY = 20
CHECK_EXTENSION = 1   # allow ONE check extension only


# -------------------------------------------------
# QUIESCENCE SEARCH (CAPTURES ONLY)
# -------------------------------------------------
def quiescence(board, alpha, beta, ply, maximizing):
    if board.is_checkmate():
        return -MATE_SCORE + ply
    if board.is_stalemate():
        return 0

    stand_pat = evaluate(board, ply)

    if maximizing:
        if stand_pat >= beta:
            return beta
        alpha = max(alpha, stand_pat)
    else:
        if stand_pat <= alpha:
            return alpha
        beta = min(beta, stand_pat)

    for move in board.legal_moves:
        if not board.is_capture(move):
            continue

        board.push(move)
        score = quiescence(board, alpha, beta, ply + 1, not maximizing)
        board.pop()

        if maximizing:
            if score >= beta:
                return beta
            alpha = max(alpha, score)
        else:
            if score <= alpha:
                return alpha
            beta = min(beta, score)

    return alpha if maximizing else beta


# -------------------------------------------------
# MINIMAX + ALPHA-BETA WITH VARIABLE DEPTH
# -------------------------------------------------
def minimax(board, depth, alpha, beta, maximizing, ply,
            ext_left, depth_counter):
    # Track deepest ply reached
    depth_counter[0] = max(depth_counter[0], ply)

    cached = lookup(board, depth)
    if cached:
        return cached

    if board.is_repetition(2):
        penalty = -REPETITION_PENALTY if maximizing else REPETITION_PENALTY
        return penalty, None

    if board.is_game_over():
        return evaluate(board, ply), None

    if depth == 0:
        if board.is_check():
            return quiescence(board, alpha, beta, ply, maximizing), None
        return evaluate(board, ply), None

    best_move = None
    moves = order_moves(board, generate_legal_moves(board))

    if maximizing:
        best_value = -float('inf')
        for move in moves:
            board.push(move)

            # -------- VARIABLE DEPTH (CHECK EXTENSION) --------
            new_depth = depth - 1
            new_ext = ext_left
            if board.is_check() and ext_left > 0:
                new_depth = depth     # extend
                new_ext -= 1
            # -------------------------------------------------

            value, _ = minimax(
                board,
                new_depth,
                alpha,
                beta,
                False,
                ply + 1,
                new_ext,
                depth_counter
            )

            board.pop()

            if value > best_value:
                best_value = value
                best_move = move

            alpha = max(alpha, value)
            if beta <= alpha:
                break
    else:
        best_value = float('inf')
        for move in moves:
            board.push(move)

            new_depth = depth - 1
            new_ext = ext_left
            if board.is_check() and ext_left > 0:
                new_depth = depth
                new_ext -= 1

            value, _ = minimax(
                board,
                new_depth,
                alpha,
                beta,
                True,
                ply + 1,
                new_ext,
                depth_counter
            )

            board.pop()

            if value < best_value:
                best_value = value
                best_move = move

            beta = min(beta, value)
            if beta <= alpha:
                break

    store(board, depth, best_value, best_move)
    return best_value, best_move


# -------------------------------------------------
# ITERATIVE DEEPENING (PRINT DEPTH USED)
# -------------------------------------------------
def iterative_deepening(board, max_depth, engine_is_black=True):
    best_move = None
    best_depth_reached = 0

    for depth in range(1, max_depth + 1):
        depth_counter = [0]

        value, move = minimax(
            board,
            depth,
            -1e9,
            1e9,
            maximizing=not engine_is_black,
            ply=0,
            ext_left=CHECK_EXTENSION,
            depth_counter=depth_counter
        )

        if move is not None:
            best_move = move
            best_depth_reached = depth_counter[0]

    print(f"[ENGINE] Move searched up to ply depth: {best_depth_reached}")
    return best_move
