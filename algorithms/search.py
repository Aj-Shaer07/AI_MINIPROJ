from evaluation import evaluate, MATE_SCORE
from move_generation import generate_legal_moves
from move_ordering import order_moves
from transposition import lookup, probe_move, store

REPETITION_PENALTY = 80          # 🔧 increased (was 20)
MAX_CHECK_EXTENSIONS = 1         # 🔧 new


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

    # CRITICAL FIX
    if board.is_check():
        moves = board.legal_moves  # ALL replies to check
    else:
        moves = (m for m in board.legal_moves if board.is_capture(m))

    for move in moves:
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
# MINIMAX + ALPHA-BETA (STABLE)
# -------------------------------------------------
def minimax(board, depth, alpha, beta, maximizing, ply=0, check_ext_used=0):
    cached = lookup(board, depth, alpha, beta)
    if cached:
        return cached

    original_alpha, original_beta = alpha, beta

    # 🔧 repetition control
    if board.is_repetition(2):
        penalty = -REPETITION_PENALTY if maximizing else REPETITION_PENALTY
        return penalty, None

    # 🔧 FORCE mate-in-1 defense (CRITICAL FIX)
    for move in board.legal_moves:
        board.push(move)
        if board.is_checkmate():
            board.pop()
            return (MATE_SCORE - ply if maximizing else -MATE_SCORE + ply), move
        board.pop()

    if board.is_game_over():
        return evaluate(board, ply), None

    # Leaf
    if depth == 0:
        if board.is_check():
            return quiescence(board, alpha, beta, ply, maximizing), None
        return evaluate(board, ply), None

    best_move = None
    tt_move = probe_move(board)
    moves = order_moves(board, generate_legal_moves(board))
    if tt_move:
        moves = [tt_move] + [m for m in moves if m != tt_move]

    if maximizing:
        best_value = -float('inf')
        for move in moves:
            board.push(move)

            new_depth = depth - 1
            new_ext = check_ext_used

            # 🔧 LIMITED check extension (max 1 per line)
            if board.is_check() and check_ext_used < MAX_CHECK_EXTENSIONS:
                new_depth = depth
                new_ext += 1

            value, _ = minimax(
                board,
                new_depth,
                alpha,
                beta,
                False,
                ply + 1,
                new_ext
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
            new_ext = check_ext_used

            if board.is_check() and check_ext_used < MAX_CHECK_EXTENSIONS:
                new_depth = depth
                new_ext += 1

            value, _ = minimax(
                board,
                new_depth,
                alpha,
                beta,
                True,
                ply + 1,
                new_ext
            )

            board.pop()

            if value < best_value:
                best_value = value
                best_move = move

            beta = min(beta, value)
            if beta <= alpha:
                break

    store(board, depth, best_value, best_move, original_alpha, original_beta)
    return best_value, best_move


# -------------------------------------------------
# ITERATIVE DEEPENING
# -------------------------------------------------
def iterative_deepening(board, max_depth, engine_is_black=True):
    best_move = None
    best_depth = 0

    for depth in range(1, max_depth + 1):
        value, move = minimax(
            board,
            depth,
            -1e9,
            1e9,
            maximizing=not engine_is_black,
            ply=0,
            check_ext_used=0
        )
        if move is not None:
            best_move = move
            best_depth = depth

    print(f"[ENGINE] Move searched up to ply depth: {best_depth}")
    return best_move

