import chess

def analyze_move(board_before: chess.Board, move: chess.Move, prev_eval_cp: int, curr_eval_cp: int, best_move_san: str | None = None, is_engine_move: bool = False) -> dict | None:
    """
    Analyzes a move and returns a categorical explanation dict representing its classification
    if it matches a rule, otherwise returns None.
    
    board_before: position BEFORE the move was played.
    move: the move played.
    prev_eval_cp: engine evaluation BEFORE the move (relative to White).
    curr_eval_cp: engine evaluation AFTER the move (relative to White).
    best_move_san: The engine's preferred move in SAN format (if available).
    is_engine_move: True if the engine played the move, False if the player played it.
    """
    board_after = board_before.copy()
    board_after.push(move)
    is_white_move = board_before.turn == chess.WHITE
    piece_color_code = 'N' if is_white_move else 'n'

    # 1. Did we deliver mate?
    if board_after.is_checkmate():
        if is_engine_move:
            return {"key": "MATE", "text": "Checkmate. Better luck next time!", "piece": piece_color_code}
        else:
            return {"key": "MATE", "text": "Checkmate! A beautifully executed finish. The game is yours.", "piece": piece_color_code}
        
    # Helpers for evaluation
    # Determine the eval difference from the perspective of the player who just moved
    if is_white_move:
        eval_diff = curr_eval_cp - prev_eval_cp
    else:
        eval_diff = prev_eval_cp - curr_eval_cp 
        
    DIFF_BLUNDER_THRESHOLD = -200
    DIFF_GREAT_THRESHOLD = 200

    # 2. Check for Great Moves
    if eval_diff > DIFF_GREAT_THRESHOLD:
        text = "Brilliant move! You found a fantastic positional or tactical resource."
        # If it's a capture, praise it
        if board_before.is_capture(move):
            text = "Great tactical find! That capture looks lethal."
        return {"key": "GREAT_MOVE", "text": text, "piece": piece_color_code}

    # 3. Check for Blunders/Missed Wins
    if eval_diff < DIFF_BLUNDER_THRESHOLD:
        blunder_piece = 'n' if is_white_move else 'N' # Opposing color horse for bad moves
        
        # Did they hang a piece or make a bad capture?
        if board_before.is_capture(move):
            text = "Oops, that capture seems to drop material."
        else:
            text = "Oops, that move drops your advantage."
            
        if best_move_san:
            text += f" A much stronger continuation was {best_move_san}."
            
        return {"key": "BLUNDER", "text": text, "piece": blunder_piece}

    # For the following minor praises (nice capture, check), ensure it wasn't a bad trade
    if eval_diff >= -50:
        # 4. Did we capture a high value piece? (Tactical but not game breaking)
        if board_before.is_capture(move):
            piece_captured = board_before.piece_at(move.to_square)
            if piece_captured:
                pt = piece_captured.piece_type
                if pt == chess.QUEEN:
                    return {"key": "NICE_CAPTURE", "text": "A tasty looking Queen you got there! Excellent.", "piece": piece_color_code}
                elif pt == chess.ROOK:
                    return {"key": "NICE_CAPTURE", "text": "Winning the exchange (a Rook)! Very nice.", "piece": piece_color_code}

        # 5. Check forcing moves
        if board_after.is_check():
            if is_engine_move:
                return {"key": "CHECK", "text": "Watch out, you're in check!", "piece": piece_color_code}
            else:
                return {"key": "CHECK", "text": "Delivering a check! Forcing moves are always good to look at.", "piece": piece_color_code}

    # 6. Early game principles
    # If the user is moving a central pawn or developing a knight/bishop in the first 15 plies
    ply_count = board_before.ply()
    if ply_count < 15 and not board_before.is_capture(move):
        piece_moved = board_before.piece_at(move.from_square)
        if piece_moved and piece_moved.piece_type in [chess.KNIGHT, chess.BISHOP]:
            # Only praise if it's a solid (non-blundering) developing move
            if eval_diff >= -50:
                return {"key": "DEVELOPMENT", "text": "Solid development. Getting minor pieces into the game is crucial.", "piece": piece_color_code}

    return None

