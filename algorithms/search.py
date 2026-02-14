import time
from dataclasses import dataclass

from evaluation import evaluate, MATE_SCORE
from move_generation import generate_legal_moves
from move_ordering import order_moves
from transposition import lookup, probe_move, store

REPETITION_PENALTY = 80
MAX_CHECK_EXTENSIONS = 1


# -------------------------------------------------
# STATS OBJECT
# -------------------------------------------------
@dataclass
class SearchStats:
    nodes: int = 0
    qnodes: int = 0
    cutoffs: int = 0

    tt_hits: int = 0
    tt_probes: int = 0

    max_ply: int = 0        # normal search ply reached
    max_qply: int = 0       # quiescence ply reached


# -------------------------------------------------
# QUIESCENCE SEARCH
# -------------------------------------------------
def quiescence(board, alpha, beta, ply, maximizing, stats: SearchStats):
    stats.qnodes += 1
    if ply > stats.max_qply:
        stats.max_qply = ply

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

    # if in check -> all legal replies
    if board.is_check():
        moves = list(board.legal_moves)
    else:
        moves = [m for m in board.legal_moves if board.is_capture(m)]

    moves = order_moves(board, moves)

    for move in moves:
        board.push(move)
        score = quiescence(board, alpha, beta, ply + 1, not maximizing, stats)
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
# MINIMAX + ALPHA-BETA
# -------------------------------------------------
def minimax(board, depth, alpha, beta, maximizing, ply, check_ext_used, stats: SearchStats):
    stats.nodes += 1
    if ply > stats.max_ply:
        stats.max_ply = ply

    cached = lookup(board, depth, alpha, beta, stats=stats)
    if cached:
        return cached

    original_alpha, original_beta = alpha, beta

    # repetition control
    if board.is_repetition(2):
        penalty = -REPETITION_PENALTY if maximizing else REPETITION_PENALTY
        return penalty, None

    # mate-in-1 detection
    for move in board.legal_moves:
        board.push(move)
        if board.is_checkmate():
            board.pop()
            return (MATE_SCORE - ply if maximizing else -MATE_SCORE + ply), move
        board.pop()

    if board.is_game_over():
        return evaluate(board, ply), None

    # leaf
    if depth == 0:
        if board.is_check():
            return quiescence(board, alpha, beta, ply, maximizing, stats), None
        return evaluate(board, ply), None

    best_move = None
    tt_move = probe_move(board)

    moves = order_moves(board, generate_legal_moves(board))
    if tt_move:
        moves = [tt_move] + [m for m in moves if m != tt_move]

    if maximizing:
        best_value = -float("inf")

        for move in moves:
            board.push(move)

            new_depth = depth - 1
            new_ext = check_ext_used

            # limited check extension
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
                new_ext,
                stats
            )
            board.pop()

            if value > best_value:
                best_value = value
                best_move = move

            alpha = max(alpha, value)
            if beta <= alpha:
                stats.cutoffs += 1
                break

    else:
        best_value = float("inf")

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
                new_ext,
                stats
            )
            board.pop()

            if value < best_value:
                best_value = value
                best_move = move

            beta = min(beta, value)
            if beta <= alpha:
                stats.cutoffs += 1
                break

    store(board, depth, best_value, best_move, original_alpha, original_beta)
    return best_value, best_move


# -------------------------------------------------
# ITERATIVE DEEPENING (RETURNS FULL INFO)
# -------------------------------------------------
def iterative_deepening(board, max_depth, engine_is_black=True):
    stats = SearchStats()
    start = time.time()

    best_move = None
    best_depth = 0
    best_value = 0

    for depth in range(1, max_depth + 1):
        value, move = minimax(
            board,
            depth,
            -1e9,
            1e9,
            maximizing=not engine_is_black,
            ply=0,
            check_ext_used=0,
            stats=stats
        )

        if move is not None:
            best_move = move
            best_depth = depth
            best_value = value

    elapsed = time.time() - start
    return best_move, best_value, best_depth, stats, elapsed


# -------------------------------------------------
# UI HELPER (FOR GUI / TERMINAL)
# -------------------------------------------------
def search_with_info(board, max_depth, engine_is_black=True):
    move, value, depth, stats, elapsed = iterative_deepening(
        board, max_depth, engine_is_black=engine_is_black
    )

    info = {
        "move": move,
        "eval_cp": int(value),
        "depth": int(depth),
        "time_ms": int(elapsed * 1000),

        "nodes": int(stats.nodes),
        "qnodes": int(stats.qnodes),
        "cutoffs": int(stats.cutoffs),

        "tt_hits": int(stats.tt_hits),
        "tt_probes": int(stats.tt_probes),

        "max_ply": int(stats.max_ply),
        "max_qply": int(stats.max_qply),
    }
    return move, info


def format_search_info(info: dict) -> str:
    return (
        f"Depth: {info['depth']} | Eval: {info['eval_cp']} cp | "
        f"Nodes: {info['nodes']} | TT hits: {info['tt_hits']} | "
        f"Cutoffs: {info['cutoffs']} | "
        f"MaxPly: {info['max_ply']} | MaxQPly: {info['max_qply']} | "
        f"Time: {info['time_ms']} ms"
    )
