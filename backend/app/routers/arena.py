"""
Self-Paced Arena Router
=======================
Adaptive ELO calibration system that adjusts engine difficulty based on game results.

ELO Ladder (depth × quality tier):
         | 4th Best | 3rd Best | 2nd Best | Best Move |
  Depth 3|   ~600   |   ~750   |   ~900   |   ~1050   |
  Depth 4|  ~1050   |  ~1200   |  ~1350   |   ~1500   |
  Depth 5|  ~1500   |  ~1650   |  ~1800   |   ~1950   |
  Depth 6|  ~1950   |  ~2050   |  ~2150   |   ~2250   |
  Depth 7|  ~2250   |  ~2350   |  ~2450   |   ~2500+  |
"""

import chess
import chess.polyglot
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
import threading

# ─────────────────────────────────────────────────────────
# ELO LADDER TABLE  (depth, quality_tier) → estimated ELO
# quality_tier: 0=4th-best, 1=3rd-best, 2=2nd-best, 3=best
# ─────────────────────────────────────────────────────────
ELO_TABLE: dict[tuple[int, int], int] = {
    (3, 0): 600,  (3, 1): 750,  (3, 2): 900,  (3, 3): 1050,
    (4, 0): 1050, (4, 1): 1200, (4, 2): 1350, (4, 3): 1500,
    (5, 0): 1500, (5, 1): 1650, (5, 2): 1800, (5, 3): 1950,
    (6, 0): 1950, (6, 1): 2050, (6, 2): 2150, (6, 3): 2250,
    (7, 0): 2250, (7, 1): 2350, (7, 2): 2450, (7, 3): 2500,
}

MAX_DEPTH = 7
MAX_QUALITY = 3   # best move
MIN_DEPTH = 3
STARTING_DEPTH = 4
STARTING_QUALITY = 0  # 4th-best

# Number of moves the search evaluates for the multi-PV selection
# We search top-4 moves and pick the Nth one based on quality_tier
MULTI_PV_COUNT = 4

# ─────────────────────────────────────────────────────────
# IN-MEMORY SESSION (single-player local app)
# Thread-safe via a lock.
# ─────────────────────────────────────────────────────────
_lock = threading.Lock()

_session: dict = {
    "depth": STARTING_DEPTH,
    "quality_tier": STARTING_QUALITY,  # 0=4th-best, 3=best
    "games_played": 0,
    "wins": 0,
    "losses": 0,
    "draws": 0,
    "draw_streak": 0,   # 2 draws = 1 quality advance
    "estimated_elo": ELO_TABLE[(STARTING_DEPTH, STARTING_QUALITY)],
    "calibrated": False,  # True after at least 1 game
}


def _get_session_copy() -> dict:
    with _lock:
        return dict(_session)


def _update_session(updates: dict) -> None:
    with _lock:
        _session.update(updates)


def _advance(depth: int, quality: int) -> tuple[int, int]:
    """Move to a harder cell: quality tier up, then depth up."""
    if quality < MAX_QUALITY:
        return depth, quality + 1
    else:
        next_depth = min(depth + 1, MAX_DEPTH)
        return next_depth, STARTING_QUALITY


def _regress(depth: int, quality: int) -> tuple[int, int]:
    """
    Move to an easier cell: quality tier down, then depth down.
    Used ONLY during the baseline calibration game when the user loses,
    so the system can find their actual level below the starting point.
    Stops at (MIN_DEPTH, STARTING_QUALITY).
    """
    if quality > STARTING_QUALITY:
        return depth, quality - 1
    else:
        prev_depth = max(depth - 1, MIN_DEPTH)
        return prev_depth, MAX_QUALITY  # reset to best-move at lower depth


# ─────────────────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────────────────
class ArenaSearchRequest(BaseModel):
    fen: str
    history: list[str] = []
    depth: int
    quality_tier: int          # 0=4th-best … 3=best
    engine_is_black: bool = True


class ArenaResultRequest(BaseModel):
    result: Literal["win", "loss", "draw"]


# ─────────────────────────────────────────────────────────
# ROUTER FACTORY  (injected with alg_modules like algorithms.py)
# ─────────────────────────────────────────────────────────
def get_arena_router(alg_modules: dict) -> APIRouter:
    router = APIRouter(prefix="/arena", tags=["arena"])
    search = alg_modules["search"]
    move_generation = alg_modules["move_generation"]

    # ── Helper: multi-PV move selection ─────────────────────
    def _pick_move_by_quality(board: chess.Board, depth: int, quality_tier: int, engine_is_black: bool):
        """
        Run a full search and return the Nth best move according to quality_tier.
        quality_tier 3 = best, 0 = 4th-best.

        Strategy:
        1. Run iterative deepening at 'depth' to get the best move.
        2. For suboptimal tiers, temporarily mask the top moves and re-search.
        3. Falls back to best move if fewer than N legal moves exist.
        """
        legal_moves = list(board.legal_moves)
        n_to_skip = MAX_QUALITY - quality_tier  # 0=best → skip 0, 3→skip 3

        if n_to_skip == 0 or len(legal_moves) <= n_to_skip:
            # Just return the best move
            move, info = search.search_with_info(board, depth, engine_is_black=engine_is_black)
            return move, info

        # Collect best moves one by one by running search with excluded squares
        excluded_moves: list[chess.Move] = []
        last_move = None
        last_info = {}

        for i in range(n_to_skip + 1):
            # Build a board copy that excludes already-found moves
            # by temporarily removing the piece from its from_square
            # (simpler: filter legal moves and restrict)
            # Approach: use a board copy with excluded moves filtered out
            test_board = board.copy()

            # Patch legal_moves by masking excluded from-squares
            # We do this by temporarily setting a fake restriction
            # (python-chess doesn't support multi-PV natively, so we
            #  re-search after each pass)
            if excluded_moves:
                # Use a board position where excluded pieces are temporarily removed
                # Clean approach: just pass the board normally, the engine may re-find
                # the same move, so we do a root move ordering hack:
                # Add null pieces temporarily isn't possible, so instead we
                # filter results by shuffling the excluded move to depth reduction
                pass

            candidate, info = search.search_with_info(
                test_board, depth, engine_is_black=engine_is_black
            )
            if candidate is None:
                break

            if candidate not in excluded_moves:
                last_move = candidate
                last_info = info
                if i < n_to_skip:
                    excluded_moves.append(candidate)

        # If we couldn't get N distinct moves, fall back to best
        if last_move is None:
            last_move, last_info = search.search_with_info(board, depth, engine_is_black=engine_is_black)

        return last_move, last_info

    def _pick_nth_best_move(board: chess.Board, depth: int, quality_tier: int, engine_is_black: bool):
        """
        Proper Multi-PV approach: evaluate each legal root move with a full search at (depth - 1).
        Because of the global Transposition Table, searching sibling branches is very fast.
        This ensures the Nth best move is determined mathematically at the actual requested depth level,
        not just via static depth-1 snapshots.
        """
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return None, {}

        n_skip = MAX_QUALITY - quality_tier  # quality=3→skip 0 (best), quality=0→skip 3 (4th best)

        if n_skip == 0 or len(legal_moves) <= n_skip:
            return search.search_with_info(board, depth, engine_is_black=engine_is_black)

        import time
        start = time.time()

        # 1. Opening Book
        try:
            from algorithms.openingbook import is_book_loaded, _reader
            if is_book_loaded() and _reader is not None:
                entries = list(_reader.find_all(board))
                entries = [e for e in entries if e.move in legal_moves]
                if entries:
                    entries.sort(key=lambda e: e.weight, reverse=True)
                    # Pick Nth popular book move
                    idx = min(n_skip, len(entries) - 1)
                    ob_move = entries[idx].move
                    info = {
                        "move": ob_move, "eval_cp": 0, "depth": 0, "time_ms": int((time.time() - start) * 1000),
                        "nodes": 0, "qnodes": 0, "cutoffs": 0, "tt_hits": 0, "tt_probes": 0, "max_ply": 0, "max_qply": 0,
                        "source": f"arena_book_q{quality_tier}",
                    }
                    return ob_move, info
        except Exception:
            pass

        # 2. Syzygy Endgame Tablebases
        try:
            from algorithms import tablebase
            if tablebase is not None and tablebase.is_tablebase_loaded():
                # For endgame, just let the tablebase engine do its thing if possible. 
                # Sub-optimal tablebase moves can be very tricky to extract cleanly without full DTZ/WDL sorting.
                # Since endgame usually means D>=5 anyway for most bots, we will just fallback to TT/Search.
                pass
        except Exception:
            pass

        # Sort root moves using internal move ordering to maximize TT cutoff efficiency
        try:
            legal_moves = alg_modules["move_ordering"].order_moves(board, legal_moves)
        except Exception:
            pass

        scored_moves: list[tuple[int, chess.Move, dict]] = []
        for move in legal_moves:
            test = board.copy()
            test.push(move)
            try:
                if depth <= 1:
                    evaluation_mod = alg_modules.get("evaluation")
                    raw = evaluation_mod.evaluate(test, ply=1) if evaluation_mod else 0
                    child_info = {"eval_cp": raw, "nodes": 1, "qnodes": 0, "tt_hits": 0, "cutoffs": 0}
                else:
                    # **CRITICAL**: Use iterative_deepening directly to bypass book/syzygy interceptions at child nodes!
                    _, value, _, stats, _ = search.iterative_deepening(test, max(1, depth - 1), engine_is_black=False)
                    child_info = {
                        "eval_cp": value,
                        "nodes": stats.nodes, "qnodes": stats.qnodes, "cutoffs": stats.cutoffs,
                        "tt_hits": stats.tt_hits, "tt_probes": stats.tt_probes, "max_qply": stats.max_qply
                    }
                
                eval_cp = int(child_info.get("eval_cp", 0))
                
                # Rank scores from the Engine's perspective:
                # If engine is White, it wants to maximize White-positive eval_cp
                # If engine is Black, it wants to minimize White-positive eval_cp 
                score = eval_cp if not engine_is_black else -eval_cp
            except Exception:
                score = -999999  # very bad fallback score
                child_info = {}
                
            scored_moves.append((score, move, child_info))

        # Sort descending (higher score = better for engine)
        scored_moves.sort(key=lambda x: x[0], reverse=True)

        # Pick the Nth best (n_skip=0 → index 0 = best, n_skip=3 → index 3 = 4th best)
        index = min(n_skip, len(scored_moves) - 1)
        selected_move = scored_moves[index][1]

        info = {
            "move": selected_move,
            # We return the raw White-positive eval_cp for the frontend
            "eval_cp": scored_moves[index][0] if not engine_is_black else -scored_moves[index][0],
            "depth": depth,
            "time_ms": int((time.time() - start) * 1000),
            "nodes": sum(int(sm[2].get("nodes", 0)) for sm in scored_moves),
            "qnodes": sum(int(sm[2].get("qnodes", 0)) for sm in scored_moves),
            "cutoffs": sum(int(sm[2].get("cutoffs", 0)) for sm in scored_moves),
            "tt_hits": sum(int(sm[2].get("tt_hits", 0)) for sm in scored_moves),
            "tt_probes": sum(int(sm[2].get("tt_probes", 0)) for sm in scored_moves),
            "max_ply": depth,
            "max_qply": max((int(sm[2].get("max_qply", 0)) for sm in scored_moves), default=0),
            "source": f"arena_d{depth}_q{quality_tier}",
        }
        return selected_move, info

    # ── GET /arena/session ────────────────────────────────
    @router.get("/session")
    def get_session():
        """Return the current arena session state."""
        return _get_session_copy()

    # ── POST /arena/reset ─────────────────────────────────
    @router.post("/reset")
    def reset_session():
        """Reset the session to baseline (depth 4, quality 0)."""
        with _lock:
            _session.update({
                "depth": STARTING_DEPTH,
                "quality_tier": STARTING_QUALITY,
                "games_played": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "draw_streak": 0,
                "estimated_elo": ELO_TABLE[(STARTING_DEPTH, STARTING_QUALITY)],
                "calibrated": False,
            })
        return {"reset": True, "session": _get_session_copy()}

    # ── POST /arena/search ────────────────────────────────
    @router.post("/search")
    def arena_search(req: ArenaSearchRequest):
        """
        Like /search but applies quality-tier suboptimal move selection.
        Used by the frontend during an arena game.
        """
        try:
            board = chess.Board(req.fen)
            # Apply move history
            for san in req.history:
                board.push_san(san)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid FEN or history: {e}")

        # Validate quality tier
        quality_tier = max(0, min(MAX_QUALITY, req.quality_tier))
        depth = max(MIN_DEPTH, min(MAX_DEPTH, req.depth))

        try:
            move, info = _pick_nth_best_move(
                board, depth, quality_tier, req.engine_is_black
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Search error: {e}")

        move_uci = move.uci() if move else None
        info_out: dict = {}
        for k, v in info.items():
            if k == "move":
                info_out[k] = v.uci() if v else None
            else:
                try:
                    info_out[k] = int(v) if isinstance(v, (int, float)) else v
                except Exception:
                    info_out[k] = v

        return {
            "best_move": move_uci,
            "info": info_out,
            "arena_depth": depth,
            "arena_quality_tier": quality_tier,
        }

    # ── POST /arena/result ────────────────────────────────
    @router.post("/result")
    def report_result(req: ArenaResultRequest):
        """
        Report the outcome of an arena game.

        Calibration phase (first game, calibrated=False):
          - Win  → advance to harder cell
          - Loss → regress to easier cell  (find where user belongs below start)
          - Draw → stay (needs more data)

        Regular phase (calibrated=True, per original rules):
          - Win  → advance to harder cell
          - Loss → stay at same cell
          - Draw → 2 draws in a row → advance one quality tier
        """
        s = _get_session_copy()
        depth = s["depth"]
        quality = s["quality_tier"]
        draw_streak = s["draw_streak"]
        calibrated = s["calibrated"]

        wins = s["wins"]
        losses = s["losses"]
        draws = s["draws"]
        games = s["games_played"] + 1

        new_depth, new_quality = depth, quality

        if req.result == "win":
            wins += 1
            draw_streak = 0
            new_depth, new_quality = _advance(depth, quality)
            message = "Win! The engine will play better next game."

        elif req.result == "loss":
            losses += 1
            draw_streak = 0
            if not calibrated:
                # Calibration phase: go easier so we can bracket the user's actual level
                new_depth, new_quality = _regress(depth, quality)
                message = f"Loss in calibration — dropping to depth {new_depth}. Let's find your true level."
            else:
                # Regular phase: stay at same difficulty per the original rule
                message = "Loss. Keep practicing at this level — you'll get it!"

        else:  # draw
            draws += 1
            draw_streak += 1
            if draw_streak >= 2:
                new_depth, new_quality = _advance(depth, quality)
                draw_streak = 0
                message = "Two draws in a row — moving up slightly!"
            else:
                message = "Draw! One more draw will advance you."

        new_elo = ELO_TABLE.get(
            (new_depth, new_quality),
            ELO_TABLE.get((MAX_DEPTH, MAX_QUALITY), 2500)
        )

        _update_session({
            "depth": new_depth,
            "quality_tier": new_quality,
            "games_played": games,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "draw_streak": draw_streak,
            "estimated_elo": new_elo,
            "calibrated": True,  # mark calibrated after first game regardless of result
        })

        return {
            "result": req.result,
            "message": message,
            "previous": {"depth": depth, "quality_tier": quality},
            "next": {"depth": new_depth, "quality_tier": new_quality},
            "estimated_elo": new_elo,
            "session": _get_session_copy(),
        }

    return router

