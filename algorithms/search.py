import chess
import time
from dataclasses import dataclass

from algorithms.evaluation import evaluate, MATE_SCORE
from algorithms.move_generation import generate_legal_moves
from algorithms.move_ordering import order_moves
from algorithms.transposition import lookup, probe_move, store

MAX_CHECK_EXTENSIONS = 3

# LMR: moves searched before reductions kick in
LMR_FULL_DEPTH_MOVES = 3
LMR_REDUCTION_LIMIT = 3  # minimum depth to start reducing
DELTA_MARGIN = 200  # Delta pruning margin in quiescence


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
# QUIESCENCE SEARCH (NEGAMAX)
# -------------------------------------------------
def quiescence(board, alpha, beta, ply, stats: SearchStats):
    """
    Negamax quiescence search — only considers captures (and all moves
    when in check) to resolve tactical sequences before returning a
    static evaluation.
    """
    stats.qnodes += 1
    if ply > stats.max_qply:
        stats.max_qply = ply

    if board.is_checkmate():
        return -MATE_SCORE + ply
    if board.is_stalemate():
        return 0

    stand_pat = evaluate(board, ply)
    # In negamax, positive = good for side to move, but our evaluate()
    # returns positive = good for White. Flip for Black.
    if not board.turn:  # Black to move
        stand_pat = -stand_pat

    if stand_pat >= beta:
        return beta
    if stand_pat > alpha:
        alpha = stand_pat

    # In check → search all moves; otherwise only captures
    in_check = board.is_check()
    if in_check:
        moves = list(board.legal_moves)
    else:
        moves = [m for m in board.legal_moves if board.is_capture(m)]

        # Delta pruning: if even capturing the best piece can't raise
        # alpha, skip remaining captures (not in check)
        if stand_pat + 1000 + DELTA_MARGIN < alpha:
            return alpha

    moves = order_moves(board, moves)

    for move in moves:
        board.push(move)
        score = -quiescence(board, -beta, -alpha, ply + 1, stats)
        board.pop()

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


# -------------------------------------------------
# NEGAMAX SEARCH WITH ALPHA-BETA + PRUNING
# -------------------------------------------------
def negamax(board, depth, alpha, beta, ply, check_ext_used, stats,
            killers, history):
    """
    Negamax alpha-beta search with:
      - Transposition table probing
      - Null-move pruning
      - Late-move reductions (LMR)
      - Principal variation search (PVS)
      - Check extensions
      - Killer / history heuristics
    """
    stats.nodes += 1
    if ply > stats.max_ply:
        stats.max_ply = ply

    # ── Repetition draw ──
    if board.is_repetition(2):
        return 0, None

    # ── TT probe ──
    cached = lookup(board, depth, alpha, beta, stats=stats)
    if cached is not None:
        return cached

    original_alpha = alpha

    # ── Terminal / game-over ──
    if board.is_game_over():
        score = evaluate(board, ply)
        if not board.turn:
            score = -score
        return score, None

    # ── Leaf node → quiescence ──
    if depth <= 0:
        return quiescence(board, alpha, beta, ply, stats), None

    in_check = board.is_check()
    tt_move = probe_move(board)

    # ── Null Move Pruning ──
    # Skip when: in check, at root, low depth, or very few pieces (zugzwang risk)
    if (not in_check and depth >= 3 and ply > 0
            and _has_non_pawn_material(board)):
        board.push(chess.Move.null())
        # Reduced-depth search
        null_score, _ = negamax(board, depth - 3, -beta, -beta + 1, ply + 1,
                                check_ext_used, stats, killers, history)
        null_score = -null_score
        board.pop()

        if null_score >= beta:
            stats.cutoffs += 1
            return beta, None

    # ── Generate and order moves ──
    moves = generate_legal_moves(board)
    ply_killers = killers.get(ply, [])
    moves = order_moves(board, moves, tt_move=tt_move,
                        killers=ply_killers, history=history)

    if not moves:
        # No legal moves: checkmate or stalemate
        score = evaluate(board, ply)
        if not board.turn:
            score = -score
        return score, None

    best_move = None
    best_value = -float("inf")
    moves_searched = 0

    for move in moves:
        is_capture = board.is_capture(move)

        board.push(move)

        new_depth = depth - 1
        new_ext = check_ext_used

        # ── Check extension ──
        if board.is_check() and check_ext_used < MAX_CHECK_EXTENSIONS:
            new_depth = depth  # don't reduce depth if extending
            new_ext += 1

        # ── PVS + LMR ──
        if moves_searched == 0:
            # First move: full window search
            value, _ = negamax(board, new_depth, -beta, -alpha, ply + 1,
                               new_ext, stats, killers, history)
            value = -value
        else:
            # ── Late Move Reductions ──
            reduction = 0
            if (moves_searched >= LMR_FULL_DEPTH_MOVES
                    and depth >= LMR_REDUCTION_LIMIT
                    and not in_check
                    and not is_capture
                    and not move.promotion):
                reduction = 1
                if moves_searched >= 6:
                    reduction = 2

            # Zero-window search (PVS) with possible LMR
            value, _ = negamax(board, new_depth - reduction, -alpha - 1, -alpha,
                               ply + 1, new_ext, stats, killers, history)
            value = -value

            # Re-search at full depth if LMR search improved alpha
            if reduction > 0 and value > alpha:
                value, _ = negamax(board, new_depth, -alpha - 1, -alpha,
                                   ply + 1, new_ext, stats, killers, history)
                value = -value

            # Re-search with full window if zero-window failed high
            if value > alpha and value < beta:
                value, _ = negamax(board, new_depth, -beta, -alpha,
                                   ply + 1, new_ext, stats, killers, history)
                value = -value

        board.pop()
        moves_searched += 1

        if value > best_value:
            best_value = value
            best_move = move

        if value > alpha:
            alpha = value
            # Update history heuristic for quiet moves that improve alpha
            if not is_capture and not move.promotion:
                h_key = (board.turn, move.from_square, move.to_square)
                history[h_key] = history.get(h_key, 0) + depth * depth

        if alpha >= beta:
            stats.cutoffs += 1
            # Store killer move
            if not is_capture and not move.promotion:
                if ply not in killers:
                    killers[ply] = []
                if move not in killers[ply]:
                    killers[ply].insert(0, move)
                    if len(killers[ply]) > 2:
                        killers[ply].pop()
            break

    store(board, depth, best_value, best_move, original_alpha, beta)
    return best_value, best_move


def _has_non_pawn_material(board):
    """Check if the side to move has at least one non-pawn, non-king piece."""
    color = board.turn
    for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        if board.pieces(pt, color):
            return True
    return False


# -------------------------------------------------
# ITERATIVE DEEPENING WITH ASPIRATION WINDOWS
# -------------------------------------------------
def iterative_deepening(board, max_depth, engine_is_black=True):
    stats = SearchStats()
    start = time.time()

    best_move = None
    best_depth = 0
    best_value = 0

    killers = {}   # {ply: [move, move]}
    history = {}   # {(color, from_sq, to_sq): int}

    # Endgame depth boost: when few pieces remain, search deeper
    # because the branching factor is much lower
    total_pieces = len(board.piece_map())
    if total_pieces <= 6:
        max_depth = max(max_depth, max_depth + 3)  # K+Q vs K, K+R vs K
    elif total_pieces <= 10:
        max_depth = max(max_depth, max_depth + 2)  # simple endgames
    elif total_pieces <= 16:
        max_depth = max(max_depth, max_depth + 1)  # middlegame-to-endgame

    prev_score = 0
    ASPIRATION_WINDOW = 50

    for depth in range(1, max_depth + 1):
        if depth <= 2:
            # No aspiration window at very low depths
            alpha = -1_000_000
            beta = 1_000_000
        else:
            # Aspiration window around previous score
            alpha = prev_score - ASPIRATION_WINDOW
            beta = prev_score + ASPIRATION_WINDOW

        value, move = negamax(
            board,
            depth,
            alpha,
            beta,
            ply=0,
            check_ext_used=0,
            stats=stats,
            killers=killers,
            history=history,
        )

        # Re-search with full window on fail-low or fail-high
        if value <= alpha or value >= beta:
            value, move = negamax(
                board,
                depth,
                -1_000_000,
                1_000_000,
                ply=0,
                check_ext_used=0,
                stats=stats,
                killers=killers,
                history=history,
            )

        if move is not None:
            best_move = move
            best_depth = depth
            best_value = value

        prev_score = value

    elapsed = time.time() - start

    # Convert negamax score back to White-positive convention for display
    if engine_is_black:
        best_value = -best_value

    return best_move, best_value, best_depth, stats, elapsed


# -------------------------------------------------
# UI HELPER (FOR GUI / TERMINAL)
# -------------------------------------------------
def search_with_info(board, max_depth, engine_is_black=True):
    # ── Opening book: forced replies ──
    # Play ...e5 against 1.e4 and ...d5 against 1.d4
    if board.fullmove_number == 1 and board.turn == chess.BLACK:
        last_move = board.peek() if board.move_stack else None
        if last_move:
            forced = None
            if last_move == chess.Move.from_uci("e2e4"):
                forced = chess.Move.from_uci("e7e5")
            elif last_move == chess.Move.from_uci("d2d4"):
                forced = chess.Move.from_uci("d7d5")
            if forced and forced in board.legal_moves:
                info = {
                    "move": forced, "eval_cp": 0, "depth": 0,
                    "time_ms": 0, "nodes": 0, "qnodes": 0,
                    "cutoffs": 0, "tt_hits": 0, "tt_probes": 0,
                    "max_ply": 0, "max_qply": 0,
                }
                return forced, info

    # Check Syzygy tablebase at root for positions with <= 4 pieces
    try:
        from algorithms import tablebase
    except Exception:
        tablebase = None

    if tablebase is not None and tablebase.is_tablebase_loaded():
        try:
            tb_move = tablebase.tablebase_move_for_root(board)
        except Exception:
            tb_move = None
        if tb_move is not None:
            info = {
                "move": tb_move,
                "eval_cp": 0,
                "depth": 0,
                "time_ms": 0,

                "nodes": 0,
                "qnodes": 0,
                "cutoffs": 0,

                "tt_hits": 0,
                "tt_probes": 0,

                "max_ply": 0,
                "max_qply": 0,
            }
            return tb_move, info

    move, value, depth, stats, elapsed = iterative_deepening(
        board, max_depth, engine_is_black=engine_is_black
    )

    if move is None:
        legal_moves = list(board.legal_moves)
        if legal_moves:
            # Fallback to the first available legal move or probe TT
            try:
                from algorithms.transposition import probe_move
                probe = probe_move(board)
                move = probe if probe in legal_moves else legal_moves[0]
            except Exception:
                move = legal_moves[0]

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


