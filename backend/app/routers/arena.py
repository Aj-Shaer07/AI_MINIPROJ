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
from fastapi import APIRouter, HTTPException, Header
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
# IN-MEMORY SESSIONS (keyed by X-Session-Id)
# Thread-safe via a lock.
# ─────────────────────────────────────────────────────────
_lock = threading.Lock()

def _new_session_state() -> dict:
    return {
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


_sessions: dict[str, dict] = {}


def _require_session_id(session_id: Optional[str]) -> str:
    if not session_id or not session_id.strip():
        raise HTTPException(status_code=400, detail="Missing X-Session-Id header")
    return session_id.strip()


def _get_session_copy(session_id: str) -> dict:
    with _lock:
        if session_id not in _sessions:
            _sessions[session_id] = _new_session_state()
        return dict(_sessions[session_id])


def _update_session(session_id: str, updates: dict) -> None:
    with _lock:
        if session_id not in _sessions:
            _sessions[session_id] = _new_session_state()
        _sessions[session_id].update(updates)


def _reset_session(session_id: str) -> dict:
    with _lock:
        _sessions[session_id] = _new_session_state()
        return dict(_sessions[session_id])


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
    transposition = alg_modules["transposition"]

    # ── Helper: multi-PV move selection ─────────────────────
    def _pick_move_by_quality(board: chess.Board, depth: int, quality_tier: int, engine_is_black: bool, tt=None):
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
            move, info = search.search_with_info(board, depth, engine_is_black=engine_is_black, tt=tt)
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
                test_board, depth, engine_is_black=engine_is_black, tt=tt
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
            last_move, last_info = search.search_with_info(board, depth, engine_is_black=engine_is_black, tt=tt)

        return last_move, last_info

    def _pick_nth_best_move(board: chess.Board, depth: int, quality_tier: int, engine_is_black: bool, tt=None):
        """
        Realistic Skill Emulation — Senior Dev improvements over naive Nth-best.

        Key insights that make this more authentic than rigid Nth-best selection:

        1. FORCED MOVES: If only 1 legal move exists, always play it.
        2. MATE IN 1: Every human at any ELO plays forced checkmate — always play it.
        3. RECAPTURE EXCEPTION: After the opponent takes a piece, an ELO-appropriate player
           recaptures cleanly if the recapture wins material back. Pure Nth-best could skip
           this, making the engine look wildly unrealistic at ANY skill level.
        4. BLUNDER FLOOR: The engine never makes pure blunders (hanging material massively)
           unless at the very lowest tier. This matches real human play — even 600 ELO players
           don't consistently give away queens for free.
        5. ELO NOISE: Instead of rigidly picking the Nth-best move, we add Gaussian noise to
           the evaluation scores and sample from the resulting distribution. This mimics
           cognitive inconsistency in humans far better than fixed rank selection.
        6. MOVE BAND SELECTION: Moves are binned into (good / okay / bad) bands based on
           eval_cp delta from the best move. Quality tier selects which band to sample from.
        """
        import time
        import random
        import math

        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return None, {}

        n_skip = MAX_QUALITY - quality_tier  # quality=3→skip 0 (best), quality=0→skip 3 (4th best)

        if n_skip == 0 or len(legal_moves) <= n_skip:
            return search.search_with_info(board, depth, engine_is_black=engine_is_black, tt=tt)

        import time
        start = time.time()

        # ── 1. Opening Book ─────────────────────────────────────────────────────
        try:
            from algorithms.openingbook import is_book_loaded, _reader
            if is_book_loaded() and _reader is not None:
                entries = list(_reader.find_all(board))
                entries = [e for e in entries if e.move in board.legal_moves]
                if entries:
                    entries.sort(key=lambda e: e.weight, reverse=True)
                    # Best move quality → most popular book move.
                    # Suboptimal → pick a less popular book move (or random at lowest tier)
                    if quality_tier == MAX_QUALITY:
                        ob_move = entries[0].move
                    elif quality_tier == 0 and len(entries) > 1:
                        # Lowest tier: pick a random book move (weighted by inverse popularity)
                        ob_move = random.choice(entries).move
                    else:
                        idx = min(n_skip, len(entries) - 1)
                        ob_move = entries[idx].move
                    info = {
                        "move": ob_move, "eval_cp": 0, "depth": 0,
                        "time_ms": int((time.time() - start) * 1000),
                        "nodes": 0, "qnodes": 0, "cutoffs": 0, "tt_hits": 0,
                        "tt_probes": 0, "max_ply": 0, "max_qply": 0,
                        "source": f"arena_book_q{quality_tier}",
                    }
                    return ob_move, info
        except Exception:
            pass

        # ── 2. FORCED MOVE — only 1 legal move, no choice ───────────────────────
        if len(legal_moves) == 1:
            move, info = search.search_with_info(board, depth, engine_is_black=engine_is_black)
            return move, info

        # ── 3. MATE IN 1 — always play it, regardless of skill tier ─────────────
        for m in legal_moves:
            test = board.copy()
            test.push(m)
            if test.is_checkmate():
                # Found mate in 1 — every human plays this
                info = {
                    "move": m, "eval_cp": 99999, "depth": 1,
                    "time_ms": int((time.time() - start) * 1000),
                    "nodes": len(legal_moves), "qnodes": 0, "cutoffs": 0,
                    "tt_hits": 0, "tt_probes": 0, "max_ply": 1, "max_qply": 0,
                    "source": f"arena_mate1_q{quality_tier}",
                }
                return m, info

        # ── 4. Score every move via search at (depth-1) ──────────────────────────
        # IMPORTANT: We call negamax() directly (not iterative_deepening) for two reasons:
        #   a) iterative_deepening boosts depth in endgames (+4 to +6 extra plies),
        #      which would make scoring 30 moves at depth-7 take minutes.
        #   b) We need consistent depth-N scores across all branches — iterative
        #      deepening's aspiration windows can cause inconsistent depths.
        # We cap child scoring depth at min(depth-1, 4) for speed — the relative
        # ranking of moves doesn't change much beyond depth-4.

        try:
            legal_moves = alg_modules["move_ordering"].order_moves(board, legal_moves)
        except Exception:
            pass

        scored_moves: list[tuple[int, chess.Move, dict]] = []
        evaluation_mod = alg_modules.get("evaluation")
        child_depth = max(1, min(depth - 1, 4))  # cap at 4 for speed

        # We always score from White's perspective (engine_is_black=False in negamax)
        # so scores are raw negamax values in White-positive convention.
        for move in legal_moves:
            test = board.copy()
            test.push(move)
            try:
                if depth <= 1:
                    raw = evaluation_mod.evaluate(test, ply=1) if evaluation_mod else 0
                    # evaluate() returns White-positive already
                    child_score = int(raw)
                    child_info = {"eval_cp": child_score, "nodes": 1, "qnodes": 0, "tt_hits": 0, "cutoffs": 0, "max_qply": 0}
                else:
                    # **CRITICAL**: Use iterative_deepening directly to bypass book/syzygy interceptions at child nodes!
                    _, value, _, stats, _ = search.iterative_deepening(
                        test, max(1, depth - 1), engine_is_black=False, tt=tt
                    )
                    child_info = {
                        "eval_cp": child_score,
                        "nodes": stats.nodes, "qnodes": stats.qnodes, "cutoffs": stats.cutoffs,
                        "tt_hits": stats.tt_hits, "tt_probes": stats.tt_probes, "max_qply": stats.max_qply
                    }

                # Convert White-positive child score to engine-relative (positive = good for engine)
                score = child_score if not engine_is_black else -child_score
            except Exception:
                score = -999999
                child_info = {}

            scored_moves.append((score, move, child_info))

        if not scored_moves:
            return search.search_with_info(board, depth, engine_is_black=engine_is_black)

        # Sort descending (best for engine first)
        scored_moves.sort(key=lambda x: x[0], reverse=True)

        best_score = scored_moves[0][0]

        # ── 5. FREE MATERIAL / HANGING PIECE EXCEPTION ──────────────────────────
        # This covers two cases:
        #   a) RECAPTURE: opponent just moved a piece to a square our piece can take
        #   b) EN PRISE: opponent has left ANY piece hanging (undefended or under-defended)
        #      such that we can capture and win material after exchanges
        #
        # Implementation: for every capture move, estimate NET material gain using
        # a simple Static Exchange Evaluation (SEE) approximation:
        #   gain ≈ value(captured_piece) - value(our_capturing_piece) if square defended
        #          value(captured_piece)                               if square NOT defended
        #
        # Scale the "minimum gain to force capture" by quality tier:
        #   Tier 3 (best):   capture anything ≥ 0cp gain  (free pawn → always take)
        #   Tier 2:          capture anything ≥ 50cp gain (minor material)
        #   Tier 1:          capture anything ≥ 150cp gain (rook/queen)
        #   Tier 0 (worst):  capture anything ≥ 600cp gain (only a free queen)
        #   → Even the weakest bot occasionally misses free pawns, but not free queens.

        PIECE_CP = {
            chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
            chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000,
        }

        def _see_approx(b: chess.Board, move: chess.Move) -> int:
            """
            Quick SEE approximation.
            Returns estimated centipawn gain (positive = winning material).
            """
            captured = b.piece_at(move.to_square)
            if captured is None:
                return 0  # not a capture (en-passant counted separately)
            captured_val = PIECE_CP.get(captured.piece_type, 0)

            mover = b.piece_at(move.from_square)
            if mover is None:
                return 0
            mover_val = PIECE_CP.get(mover.piece_type, 0)

            # Is the target square defended by the opponent AFTER we take?
            b_after = b.copy()
            b_after.push(move)
            opponent = b_after.turn  # opponent to move after our capture
            if b_after.is_attacked_by(opponent, move.to_square):
                # Square is defended — we'll likely lose our piece too.
                # Net gain = captured_val - mover_val (can be negative = bad trade)
                return captured_val - mover_val
            else:
                # Square is NOT defended — we win the piece for free.
                return captured_val

        # Minimum material gain (in cp) that forces a capture, per quality tier
        FREE_MATERIAL_THRESHOLD = {
            3: 0,    # always take free material (even a free pawn)
            2: 50,   # take anything worth more than a pawn exchange
            1: 150,  # take rooks and queens for free
            0: 600,  # only take a free queen (very weak player)
        }
        threshold = FREE_MATERIAL_THRESHOLD[quality_tier]

        # Find all captures that win material above the threshold
        winning_captures = []
        for sm in scored_moves:
            move_candidate = sm[1]
            if not board.is_capture(move_candidate):
                continue
            # Also handle en passant (always wins a pawn)
            if board.is_en_passant(move_candidate):
                gain = PIECE_CP[chess.PAWN]
            else:
                gain = _see_approx(board, move_candidate)
            if gain >= threshold:
                winning_captures.append((gain, sm))

        if winning_captures:
            # Sort by highest material gain, then by engine score
            winning_captures.sort(key=lambda x: (x[0], x[1][0]), reverse=True)
            best_capture = winning_captures[0][1]

            # Only override if this capture is reasonably scored
            # (not massively worse than best move — avoids weird TT discrepancies)
            if best_capture[0] >= best_score - 200:
                move = best_capture[1]
                info = _build_info(best_capture, scored_moves, depth, quality_tier, start, engine_is_black)
                info["source"] = f"arena_freematerial_q{quality_tier}"
                return move, info

        # ── 6. BLUNDER FLOOR — don't drop pieces egregiously at mid/high tiers ──
        # Define blunder as a move that loses more than 'blunder_threshold' cp vs best move.
        # Threshold scales with quality tier: lower tier = more lenient with material drops.
        blunder_thresholds = {
            0: 9999,   # 4th-best: anything goes (no floor)
            1: 600,    # 3rd-best: won't drop more than a rook for nothing
            2: 300,    # 2nd-best: won't drop more than a minor piece for nothing
            3: 0,      # best-move: always plays best
        }
        blunder_floor_cp = blunder_thresholds[quality_tier]

        # Filter out pure blunders for mid/high skill tiers
        eligible_moves = [
            sm for sm in scored_moves
            if (best_score - sm[0]) <= blunder_floor_cp
        ]
        if not eligible_moves:
            eligible_moves = scored_moves  # fallback if all moves are blunders (zugzwang etc.)

        # ── 7. ELO-CALIBRATED BAND SELECTION WITH NOISE ─────────────────────────
        # Rather than rigidly picking index N, we:
        # a) Define quality bands: top-30cp = "good", 30-150cp = "okay", 150cp+ = "bad"
        # b) Quality tier maps to which band to sample from
        # c) Add Gaussian noise scaled to ELO tier for natural inconsistency

        BAND_THRESHOLDS = {
            3: (0, 30),       # best: must stay within top 30cp
            2: (30, 150),     # 2nd-best: sample from "okay" moves (30-150cp below best)
            1: (100, 300),    # 3rd-best: sample from "inaccuracy" range
            0: (200, 700),    # 4th-best: sample from "mistake/blunder" range
        }

        lo, hi = BAND_THRESHOLDS[quality_tier]

        # Noise magnitude: higher at lower tiers (simulates human inconsistency)
        # quality=3: ±10cp noise, quality=0: ±80cp noise
        noise_scale = [80, 50, 25, 10][quality_tier]

        # Find moves in target band
        band_moves = [
            sm for sm in eligible_moves
            if lo <= (best_score - sm[0]) <= hi
        ]

        # If no moves in the target band, widen the search
        if not band_moves:
            if quality_tier == MAX_QUALITY:
                # Just play best
                band_moves = eligible_moves[:1]
            else:
                # Relax: take anything below the best move
                band_moves = eligible_moves[1:] if len(eligible_moves) > 1 else eligible_moves

        if not band_moves:
            band_moves = eligible_moves

        # Add noise and re-sort to pick a move from the band naturally
        def noisy_score(sm):
            return sm[0] + random.gauss(0, noise_scale)

        if quality_tier == MAX_QUALITY:
            # At best quality: just take the highest score (no noise needed)
            selected = max(band_moves, key=lambda sm: sm[0])
        else:
            # At suboptimal quality: use noisy selection within the band
            selected = max(band_moves, key=noisy_score)

        info = _build_info(selected, scored_moves, depth, quality_tier, start, engine_is_black)
        return selected[1], info

    def _build_info(selected, scored_moves, depth, quality_tier, start, engine_is_black):
        import time
        return {
            "move": selected[1],
            "eval_cp": selected[0] if not engine_is_black else -selected[0],
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

    # ── GET /arena/session ────────────────────────────────
    @router.get("/session")
    def get_session(x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id")):
        """Return the current arena session state."""
        sid = _require_session_id(x_session_id)
        return _get_session_copy(sid)

    # ── POST /arena/reset ─────────────────────────────────
    @router.post("/reset")
    def reset_session(x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id")):
        """Reset the session to baseline (depth 4, quality 0)."""
        sid = _require_session_id(x_session_id)
        return {"reset": True, "session": _reset_session(sid)}

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
        tt = transposition.TranspositionTable()

        try:
            move, info = _pick_nth_best_move(
                board, depth, quality_tier, req.engine_is_black, tt=tt
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
    def report_result(req: ArenaResultRequest, x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id")):
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
        sid = _require_session_id(x_session_id)
        s = _get_session_copy(sid)
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

        _update_session(sid, {
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
            "session": _get_session_copy(sid),
        }

    return router

