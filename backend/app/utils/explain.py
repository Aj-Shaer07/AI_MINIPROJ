import chess
from typing import Optional

# ─────────────────────────────────────────────────────────
# PIECE NAMES & VALUES  (for readable text)
# ─────────────────────────────────────────────────────────
PIECE_NAME = {
    chess.PAWN: "pawn", chess.KNIGHT: "knight", chess.BISHOP: "bishop",
    chess.ROOK: "rook", chess.QUEEN: "queen", chess.KING: "king",
}
PIECE_VALUE = {
    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000,
}
CENTER_SQUARES = {chess.E4, chess.D4, chess.E5, chess.D5}
EXTENDED_CENTER = {chess.C3, chess.D3, chess.E3, chess.F3,
                   chess.C4, chess.D4, chess.E4, chess.F4,
                   chess.C5, chess.D5, chess.E5, chess.F5,
                   chess.C6, chess.D6, chess.E6, chess.F6}


# ─────────────────────────────────────────────────────────
# GAME PHASE DETECTION
# ─────────────────────────────────────────────────────────
def _game_phase(board: chess.Board) -> str:
    """Return 'opening', 'middlegame', or 'endgame'."""
    phase = 0
    phase_weight = {chess.KNIGHT: 1, chess.BISHOP: 1, chess.ROOK: 2, chess.QUEEN: 4}
    for pt, w in phase_weight.items():
        phase += len(board.pieces(pt, chess.WHITE)) * w
        phase += len(board.pieces(pt, chess.BLACK)) * w

    if board.ply() < 12 and phase >= 20:
        return "opening"
    elif phase <= 8:
        return "endgame"
    return "middlegame"


# ─────────────────────────────────────────────────────────
# TACTICAL PATTERN DETECTION
# ─────────────────────────────────────────────────────────
def _detect_pin(board: chess.Board, color: chess.Color) -> Optional[str]:
    """Detect if `color` has a piece pinned to their king."""
    king_sq = board.king(color)
    if king_sq is None:
        return None
    enemy = not color

    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece and piece.color == color and piece.piece_type != chess.KING:
            # Check if removing this piece would expose king to attack
            test_board = board.copy()
            test_board.remove_piece_at(sq)
            if test_board.is_attacked_by(enemy, king_sq):
                return PIECE_NAME.get(piece.piece_type, "piece")
    return None


def _detect_fork(board: chess.Board, move: chess.Move) -> Optional[str]:
    """Detect if a move creates a fork (the moved piece attacks multiple high-value pieces)."""
    board_after = board.copy()
    board_after.push(move)
    attacker = board.piece_at(move.from_square)
    if not attacker:
        return None

    attacked_pieces = []
    enemy = not attacker.color
    to_sq = move.to_square

    # Get squares specifically attacked BY the piece on to_sq (not just any piece)
    # Use board_after.attacks(to_sq) which returns the set of squares attacked from to_sq
    try:
        attacked_squares = board_after.attacks(to_sq)
    except Exception:
        return None

    for sq in attacked_squares:
        target = board_after.piece_at(sq)
        if target and target.color == enemy and target.piece_type != chess.PAWN:
            attacked_pieces.append(target.piece_type)

    # A fork needs at least 2 valuable pieces attacked by the SAME piece
    valuable = [p for p in attacked_pieces if p in (chess.KING, chess.QUEEN, chess.ROOK)]
    if len(valuable) >= 2:
        names = " and ".join(PIECE_NAME[p] for p in valuable[:2])
        return f"forking the {names}"
    # Also count knight/bishop forks on queen+rook or similar
    if attacker.piece_type in (chess.KNIGHT, chess.PAWN) and len(attacked_pieces) >= 2:
        high_value = [p for p in attacked_pieces if p in (chess.KING, chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)]
        if len(high_value) >= 2 and any(p in (chess.KING, chess.QUEEN, chess.ROOK) for p in high_value):
            names = " and ".join(PIECE_NAME[p] for p in high_value[:2])
            return f"forking the {names}"
    return None


def _is_back_rank_weak(board: chess.Board, color: chess.Color) -> bool:
    """Check if the back rank is weak (king on 1st/8th rank, no escape, pawns blocking)."""
    king_sq = board.king(color)
    if king_sq is None:
        return False
    king_rank = chess.square_rank(king_sq)
    back_rank = 0 if color == chess.WHITE else 7
    if king_rank != back_rank:
        return False

    # Check if king has any escape squares
    king_file = chess.square_file(king_sq)
    for df in (-1, 0, 1):
        escape_file = king_file + df
        escape_rank = back_rank + (1 if color == chess.WHITE else -1)
        if 0 <= escape_file <= 7 and 0 <= escape_rank <= 7:
            escape_sq = chess.square(escape_file, escape_rank)
            piece = board.piece_at(escape_sq)
            # Escape exists if square is empty or has enemy piece, and isn't attacked
            if (not piece or piece.color != color) and not board.is_attacked_by(not color, escape_sq):
                return False
    return True


def _detect_discovered_attack(board: chess.Board, move: chess.Move) -> Optional[str]:
    """Detect if moving a piece uncovers an attack on a valuable enemy piece
    by a DIFFERENT piece behind it (a true discovered attack)."""
    mover = board.piece_at(move.from_square)
    if not mover:
        return None

    board_after = board.copy()
    board_after.push(move)
    enemy = not mover.color
    to_sq = move.to_square

    # Get the squares attacked by the piece that just moved (from its new square)
    try:
        mover_attacks_after = board_after.attacks(to_sq)
    except Exception:
        mover_attacks_after = set()

    for sq in chess.SQUARES:
        target = board_after.piece_at(sq)
        if target and target.color == enemy and target.piece_type in (chess.QUEEN, chess.ROOK, chess.KING):
            # Is this target now attacked?
            now_attacked = board_after.is_attacked_by(mover.color, sq)
            if not now_attacked:
                continue
            # Was it attacked before the move?
            was_attacked = board.is_attacked_by(mover.color, sq)
            if was_attacked:
                continue
            # It's a new attack. But is it the mover doing the attacking, or a piece behind it?
            # If the target is in the mover's attack set, it's a direct attack, not discovered.
            if sq in mover_attacks_after:
                continue
            # It's a discovered attack — a piece behind the mover is now hitting the target
            return f"discovering an attack on the {PIECE_NAME[target.piece_type]}"
    return None


# ─────────────────────────────────────────────────────────
# POSITIONAL ANALYSIS HELPERS
# ─────────────────────────────────────────────────────────
def _count_center_control(board: chess.Board, color: chess.Color) -> int:
    """Count how many center squares are controlled by `color`."""
    count = 0
    for sq in CENTER_SQUARES:
        if board.is_attacked_by(color, sq):
            count += 1
        piece = board.piece_at(sq)
        if piece and piece.color == color:
            count += 1
    return count


def _has_bishop_pair(board: chess.Board, color: chess.Color) -> bool:
    return len(board.pieces(chess.BISHOP, color)) >= 2


def _count_open_files_for_rooks(board: chess.Board, color: chess.Color) -> int:
    """Count rooks on open or semi-open files."""
    count = 0
    for sq in board.pieces(chess.ROOK, color):
        f = chess.square_file(sq)
        own_pawns = any(chess.square_file(s) == f for s in board.pieces(chess.PAWN, color))
        if not own_pawns:
            count += 1
    return count


def _find_passed_pawns(board: chess.Board, color: chess.Color) -> list:
    """Find passed pawns for the given color."""
    passed = []
    enemy = not color
    for sq in board.pieces(chess.PAWN, color):
        f = chess.square_file(sq)
        r = chess.square_rank(sq)
        adj_files = [af for af in (f - 1, f, f + 1) if 0 <= af <= 7]
        is_passed = True
        for ep_sq in board.pieces(chess.PAWN, enemy):
            ep_f = chess.square_file(ep_sq)
            ep_r = chess.square_rank(ep_sq)
            if ep_f in adj_files:
                if color == chess.WHITE and ep_r > r:
                    is_passed = False
                    break
                elif color == chess.BLACK and ep_r < r:
                    is_passed = False
                    break
        if is_passed:
            passed.append(sq)
    return passed


def _find_hanging_pieces(board: chess.Board, color: chess.Color) -> list:
    """Find pieces that are attacked but not defended."""
    hanging = []
    enemy = not color
    for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        for sq in board.pieces(pt, color):
            if board.is_attacked_by(enemy, sq) and not board.is_attacked_by(color, sq):
                hanging.append((pt, sq))
    return hanging


def _king_safety_score(board: chess.Board, color: chess.Color) -> int:
    """Simple king safety heuristic (higher = safer). Range roughly 0-6."""
    king_sq = board.king(color)
    if king_sq is None:
        return 0
    score = 0
    king_file = chess.square_file(king_sq)
    king_rank = chess.square_rank(king_sq)

    # Pawn shield
    shield_files = [max(0, king_file - 1), king_file, min(7, king_file + 1)]
    front_rank = king_rank + (1 if color == chess.WHITE else -1)
    if 0 <= front_rank <= 7:
        for sf in shield_files:
            shield_sq = chess.square(sf, front_rank)
            piece = board.piece_at(shield_sq)
            if piece and piece.piece_type == chess.PAWN and piece.color == color:
                score += 1

    # Castled bonus
    if color == chess.WHITE:
        if king_file in (1, 2, 6) and king_rank == 0:  # castled position
            score += 2
    else:
        if king_file in (1, 2, 6) and king_rank == 7:
            score += 2

    return score


def _material_balance(board: chess.Board) -> int:
    """Material balance in centipawns. Positive = White advantage."""
    balance = 0
    for pt, val in PIECE_VALUE.items():
        if pt != chess.KING:
            balance += len(board.pieces(pt, chess.WHITE)) * val
            balance -= len(board.pieces(pt, chess.BLACK)) * val
    return balance


# ─────────────────────────────────────────────────────────
# MOVE FEATURE EXTRACTION
# ─────────────────────────────────────────────────────────
def _describe_move_features(board_before: chess.Board, move: chess.Move) -> list[str]:
    """Extract a list of descriptive features about a move."""
    features = []
    board_after = board_before.copy()
    board_after.push(move)
    mover = board_before.piece_at(move.from_square)
    if not mover:
        return features
    mover_name = PIECE_NAME.get(mover.piece_type, "piece")
    color = mover.color
    enemy = not color

    # 1. Capture analysis
    if board_before.is_capture(move):
        captured = board_before.piece_at(move.to_square)
        # Handle en passant: captured pawn is not on to_square
        if not captured and board_before.is_en_passant(move):
            features.append("captures en passant")
        elif captured:
            cap_name = PIECE_NAME.get(captured.piece_type, "piece")
            cap_val = PIECE_VALUE.get(captured.piece_type, 0)
            mover_val = PIECE_VALUE.get(mover.piece_type, 0)
            if cap_val > mover_val + 50:
                features.append(f"wins the {cap_name} (material advantage)")
            elif cap_val < mover_val - 50:
                features.append(f"sacrifices the {mover_name} for a {cap_name}")
            elif mover.piece_type == captured.piece_type:
                features.append(f"trades {mover_name}s")
            else:
                features.append(f"trades the {mover_name} for a {cap_name}")

    # 2. Check
    if board_after.is_check():
        features.append("delivers check")

    # 3. Checkmate
    if board_after.is_checkmate():
        features.append("delivers checkmate")
        return features  # Nothing else matters

    # 4. Center control change
    center_before = _count_center_control(board_before, color)
    center_after = _count_center_control(board_after, color)
    if center_after > center_before:
        features.append("increases central control")

    # 5. Piece development (opening)
    phase = _game_phase(board_before)
    if phase == "opening":
        if mover.piece_type in (chess.KNIGHT, chess.BISHOP):
            if move.to_square in EXTENDED_CENTER:
                features.append(f"develops the {mover_name} to an active square")
            else:
                features.append(f"develops the {mover_name}")

    # 6. Castling
    if board_before.is_castling(move):
        features.append("castles to improve king safety")

    # 7. Pawn advancement & promotion
    if mover.piece_type == chess.PAWN:
        # 7a. Pawn promotion
        if move.promotion:
            promo_name = PIECE_NAME.get(move.promotion, "piece")
            features.append(f"promotes the pawn to a {promo_name}")
        else:
            rank = chess.square_rank(move.to_square)
            effective_rank = rank if color == chess.WHITE else (7 - rank)
            # Check if this pawn is actually passed
            passed_pawns = _find_passed_pawns(board_after, color)
            is_passed_pawn = move.to_square in passed_pawns
            if is_passed_pawn and effective_rank >= 4:
                ordinal = {4: "5th", 5: "6th", 6: "7th"}
                features.append(f"advances a passed pawn to the {ordinal.get(effective_rank, str(effective_rank + 1) + 'th')} rank")
            elif effective_rank >= 5:
                ordinal = {5: "6th", 6: "7th"}
                features.append(f"pushes a pawn to the {ordinal.get(effective_rank, str(effective_rank + 1) + 'th')} rank")
            if move.to_square in CENTER_SQUARES:
                features.append("occupies the center")

    # 8. Creates a NEW pin (not one that already existed)
    pinned_before = _detect_pin(board_before, enemy)
    pinned_after = _detect_pin(board_after, enemy)
    if pinned_after and pinned_after != pinned_before:
        features.append(f"pins the opponent's {pinned_after}")

    # 9. Fork detection
    fork = _detect_fork(board_before, move)
    if fork:
        features.append(fork)

    # 10. Discovered attack
    discovered = _detect_discovered_attack(board_before, move)
    if discovered:
        features.append(discovered)

    # 11. Back rank threat
    if _is_back_rank_weak(board_after, enemy):
        if board_after.is_check() or mover.piece_type in (chess.ROOK, chess.QUEEN):
            features.append("exploits back-rank weakness")

    # 12. Open file for rook
    if mover.piece_type == chess.ROOK:
        to_file = chess.square_file(move.to_square)
        own_pawns_on_file = any(chess.square_file(s) == to_file for s in board_after.pieces(chess.PAWN, color))
        if not own_pawns_on_file:
            features.append("places the rook on an open file")

    # 13. King safety impact
    if phase == "middlegame":
        safety_before = _king_safety_score(board_before, enemy)
        safety_after = _king_safety_score(board_after, enemy)
        if safety_after < safety_before:
            features.append("weakens the opponent's king safety")

    # 14. Creates a passed pawn
    passed_before = len(_find_passed_pawns(board_before, color))
    passed_after = len(_find_passed_pawns(board_after, color))
    if passed_after > passed_before:
        features.append("creates a passed pawn")

    # 15. Hangs a piece (negative feature)
    hanging_after = _find_hanging_pieces(board_after, color)
    if hanging_after:
        piece_name = PIECE_NAME.get(hanging_after[0][0], "piece")
        features.append(f"leaves the {piece_name} undefended")

    return features


# ─────────────────────────────────────────────────────────
# PUBLIC API: ANALYZE PLAYER MOVE  (real-time + post-game)
# ─────────────────────────────────────────────────────────
def analyze_move(
    board_before: chess.Board,
    move: chess.Move,
    prev_eval_cp: int,
    curr_eval_cp: int,
    best_move_san: str | None = None,
    is_engine_move: bool = False,
) -> dict | None:
    """
    Analyze a player's move and return a rich explanation dict.

    Returns:
        dict with keys: 'key', 'text', 'piece'
        or None if no noteworthy explanation.
    """
    board_after = board_before.copy()
    board_after.push(move)
    is_white_move = board_before.turn == chess.WHITE
    piece_color_code = 'N' if is_white_move else 'n'
    color = board_before.turn
    phase = _game_phase(board_before)

    # Eval diff from the mover's perspective
    if is_white_move:
        eval_diff = curr_eval_cp - prev_eval_cp
    else:
        eval_diff = prev_eval_cp - curr_eval_cp

    features = _describe_move_features(board_before, move)

    # ── 1. Checkmate ──
    if board_after.is_checkmate():
        if is_engine_move:
            return {"key": "MATE", "text": "Checkmate. The engine finishes the game.", "piece": piece_color_code}
        else:
            return {"key": "MATE", "text": "Checkmate! A decisive finish — well played.", "piece": piece_color_code}

    # ── 2. Brilliant / Great Moves (eval_diff > +200) ──
    if eval_diff > 200:
        tactical_features = [f for f in features if any(k in f for k in
            ["fork", "pin", "discover", "back-rank", "check", "wins", "passed pawn"])]

        if tactical_features:
            detail = tactical_features[0]
            text = f"Brilliant move! This {detail}."
        elif board_before.is_capture(move):
            text = "Excellent tactical strike! This capture significantly improves your position."
        else:
            text = "Outstanding move! You found a strong positional resource."

        if phase == "endgame" and eval_diff > 400:
            text = "Precise endgame technique! This move converts your advantage decisively."

        return {"key": "GREAT_MOVE", "text": text, "piece": piece_color_code}

    # ── 3. Good Moves (eval_diff > +50) ──
    if eval_diff > 50:
        if features:
            detail = features[0]
            text = f"Good move. This {detail}."
        elif board_before.is_capture(move):
            text = "Solid capture. You're maintaining or improving your position."
        else:
            text = "A strong continuation that improves your position."
        return {"key": "GOOD_MOVE", "text": text, "piece": piece_color_code}

    # ── 4. Blunders (eval_diff < -200) ──
    if eval_diff < -200:
        blunder_piece = 'n' if is_white_move else 'N'
        negative_features = [f for f in features if any(k in f for k in ["undefended", "leaves", "sacrifices"])]

        if board_before.is_capture(move):
            text = "This capture loses material."
        elif negative_features:
            text = f"Critical error — this {negative_features[0]}."
        else:
            text = "This move significantly worsens your position."

        return {"key": "BLUNDER", "text": text, "piece": blunder_piece}

    # ── 5. Mistakes (eval_diff < -100) ──
    if eval_diff < -100:
        blunder_piece = 'n' if is_white_move else 'N'
        text = "This move is a mistake — it hands the opponent an advantage."
        return {"key": "MISTAKE", "text": text, "piece": blunder_piece}

    # ── 6. Minor Inaccuracies (eval_diff < -50) ──
    if eval_diff < -50:
        blunder_piece = 'n' if is_white_move else 'N'
        text = "Slight inaccuracy. There was a more precise continuation available."
        return {"key": "INACCURACY", "text": text, "piece": blunder_piece}

    # ── 7. Neutral but noteworthy moves ──
    if eval_diff >= -50:
        # Praise nice captures
        if board_before.is_capture(move):
            captured = board_before.piece_at(move.to_square)
            if captured and captured.piece_type == chess.QUEEN:
                return {"key": "NICE_CAPTURE", "text": "Winning the Queen! That's a massive gain.", "piece": piece_color_code}
            elif captured and captured.piece_type == chess.ROOK:
                return {"key": "NICE_CAPTURE", "text": "Winning the exchange — excellent.", "piece": piece_color_code}

        # Praise forcing moves
        if board_after.is_check():
            if is_engine_move:
                return {"key": "CHECK", "text": "Check! Your king is under attack.", "piece": piece_color_code}
            else:
                return {"key": "CHECK", "text": "Keeping the pressure with a check — forcing moves are powerful.", "piece": piece_color_code}

        # Opening principles
        if phase == "opening":
            mover = board_before.piece_at(move.from_square)
            if mover:
                if mover.piece_type in (chess.KNIGHT, chess.BISHOP) and not board_before.is_capture(move):
                    return {"key": "DEVELOPMENT", "text": "Good development. Getting minor pieces active early is key.", "piece": piece_color_code}
                if board_before.is_castling(move):
                    return {"key": "CASTLE", "text": "Castling — connecting the rooks and securing the king.", "piece": piece_color_code}

    return None


# ─────────────────────────────────────────────────────────
# PUBLIC API: ANALYZE ENGINE MOVE  (real-time popup)
# ─────────────────────────────────────────────────────────
def analyze_engine_move(
    board_before: chess.Board,
    move: chess.Move,
    prev_eval_cp: int,
    curr_eval_cp: int,
) -> dict | None:
    """
    Explain why the engine played a particular move.
    Used for the real-time ExplainPopup during gameplay.
    """
    board_after = board_before.copy()
    board_after.push(move)
    is_white = board_before.turn == chess.WHITE
    piece_code = 'N' if is_white else 'n'
    phase = _game_phase(board_before)

    features = _describe_move_features(board_before, move)

    # Filter to the most interesting features
    tactical = [f for f in features if any(k in f for k in
        ["checkmate", "check", "fork", "pin", "discover", "back-rank", "wins", "passed"])]
    positional = [f for f in features if any(k in f for k in
        ["central", "develops", "castles", "open file", "king safety", "center"])]

    # Checkmate
    if board_after.is_checkmate():
        return {"key": "MATE", "text": "Checkmate. The engine finishes the game.", "piece": piece_code}

    # Tactical explanations take priority
    if tactical:
        detail = tactical[0]
        text = f"The engine {detail}."
        return {"key": "ENGINE_TACTIC", "text": text, "piece": piece_code}

    # Capture explanation
    if board_before.is_capture(move):
        captured = board_before.piece_at(move.to_square)
        if captured:
            cap_name = PIECE_NAME.get(captured.piece_type, "piece")
            mover = board_before.piece_at(move.from_square)
            mover_val = PIECE_VALUE.get(mover.piece_type, 0) if mover else 0
            cap_val = PIECE_VALUE.get(captured.piece_type, 0)
            if cap_val > mover_val + 50:
                return {"key": "ENGINE_CAPTURE", "text": f"The engine wins your {cap_name} — a significant material gain.", "piece": piece_code}
            elif cap_val == mover_val or abs(cap_val - mover_val) <= 50:
                return {"key": "ENGINE_CAPTURE", "text": f"The engine exchanges pieces, trading a {PIECE_NAME.get(mover.piece_type, 'piece') if mover else 'piece'} for your {cap_name}.", "piece": piece_code}
            else:
                return {"key": "ENGINE_CAPTURE", "text": f"The engine captures your {cap_name}.", "piece": piece_code}

    # Check
    if board_after.is_check():
        return {"key": "ENGINE_CHECK", "text": "The engine delivers check — your king must respond.", "piece": piece_code}

    # Positional explanations
    if positional:
        detail = positional[0]
        text = f"The engine {detail}."
        return {"key": "ENGINE_POSITIONAL", "text": text, "piece": piece_code}

    # Phase-specific fallbacks
    if phase == "opening":
        mover = board_before.piece_at(move.from_square)
        if mover:
            if mover.piece_type in (chess.KNIGHT, chess.BISHOP):
                return {"key": "ENGINE_DEV", "text": "The engine develops a minor piece — fighting for early activity.", "piece": piece_code}
            if mover.piece_type == chess.PAWN and move.to_square in EXTENDED_CENTER:
                return {"key": "ENGINE_CENTER", "text": "The engine pushes a pawn to contest the center.", "piece": piece_code}
            if board_before.is_castling(move):
                return {"key": "ENGINE_CASTLE", "text": "The engine castles — securing the king and connecting the rooks.", "piece": piece_code}

    if phase == "endgame":
        mover = board_before.piece_at(move.from_square)
        if mover and mover.piece_type == chess.KING:
            return {"key": "ENGINE_ENDGAME", "text": "The engine activates the king — a key endgame principle.", "piece": piece_code}
        if mover and mover.piece_type == chess.PAWN:
            rank = chess.square_rank(move.to_square)
            eff_rank = rank if is_white else (7 - rank)
            if eff_rank >= 5:
                return {"key": "ENGINE_PASSER", "text": "The engine pushes a pawn towards promotion.", "piece": piece_code}

    # Eval-based fallback
    mat_balance = _material_balance(board_after)
    side_advantage = mat_balance if is_white else -mat_balance
    if side_advantage > 200:
        return {"key": "ENGINE_CONSOLIDATE", "text": "The engine consolidates its winning advantage.", "piece": piece_code}
    elif side_advantage < -200:
        return {"key": "ENGINE_DEFEND", "text": "The engine defends tenaciously in a tough position.", "piece": piece_code}

    return {"key": "ENGINE_MOVE", "text": "The engine makes a quiet positional move, improving piece coordination.", "piece": piece_code}


# ─────────────────────────────────────────────────────────
# PUBLIC API: EXPLAIN BEST MOVE  (post-game analysis)
# ─────────────────────────────────────────────────────────
def explain_best_move(
    board_before: chess.Board,
    played_move: chess.Move,
    best_move_obj: chess.Move,
    best_move_san: str,
    annotation: str,
) -> str | None:
    """
    For post-game analysis: explain WHY the best move is better than the played move.
    Returns a full explanation string, or None.
    """
    if annotation not in ("BLUNDER", "MISTAKE", "INACCURACY"):
        return None
    
    best_features = _describe_move_features(board_before, best_move_obj)
    played_features = _describe_move_features(board_before, played_move)

    # Find features the best move has that the played move doesn't
    unique_best = [f for f in best_features if f not in played_features
                   and "undefended" not in f and "leaves" not in f]
    # Find negative features the played move has
    played_negatives = [f for f in played_features if any(k in f for k in ["undefended", "leaves", "sacrifices"])]

    parts = []

    # Describe what went wrong with the played move
    if played_negatives:
        parts.append(f"Your move {played_negatives[0]}.")
    else:
        severity = {"BLUNDER": "a serious error", "MISTAKE": "a mistake", "INACCURACY": "slightly imprecise"}
        parts.append(f"Your move was {severity.get(annotation, 'imprecise')}.")

    # Describe why the best move was better
    if unique_best:
        # Pick the best 1-2 reasons
        reasons = unique_best[:2]
        reason_text = " and ".join(reasons)
        parts.append(f"Instead, {best_move_san} {reason_text}.")
    else:
        # Fallback: analyze the best move's tactical nature
        if board_before.is_capture(best_move_obj):
            captured = board_before.piece_at(best_move_obj.to_square)
            if captured:
                cap_name = PIECE_NAME.get(captured.piece_type, "piece")
                parts.append(f"Instead, {best_move_san} wins the {cap_name}.")
            else:
                parts.append(f"Instead, {best_move_san} makes a stronger capture.")
        elif board_before.gives_check(best_move_obj):
            parts.append(f"Instead, {best_move_san} delivers check, keeping the initiative.")
        else:
            # Positional reasoning based on the best move's destination
            to_sq = best_move_obj.to_square
            mover = board_before.piece_at(best_move_obj.from_square)
            if mover:
                mover_name = PIECE_NAME[mover.piece_type]
                if to_sq in CENTER_SQUARES:
                    parts.append(f"Instead, {best_move_san} places the {mover_name} in the center, fighting for control.")
                elif mover.piece_type in (chess.KNIGHT, chess.BISHOP) and board_before.ply() < 20:
                    parts.append(f"Instead, {best_move_san} develops the {mover_name} to a more active square.")
                elif mover.piece_type == chess.ROOK:
                    to_file = chess.square_file(to_sq)
                    own_pawns = any(chess.square_file(s) == to_file
                                    for s in board_before.pieces(chess.PAWN, mover.color))
                    if not own_pawns:
                        parts.append(f"Instead, {best_move_san} places the rook on an open file.")
                    else:
                        parts.append(f"Instead, {best_move_san} finds a stronger square for the {mover_name}.")
                else:
                    parts.append(f"Instead, {best_move_san} improves the position of the {mover_name}.")
            else:
                parts.append(f"Instead, {best_move_san} was the stronger continuation.")

    return " ".join(parts)
