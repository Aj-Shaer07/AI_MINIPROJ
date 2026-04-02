from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, cast
import chess
from app.utils import explain

def get_router(modules: Dict[str, Any]) -> APIRouter:
    evaluation = modules["evaluation"]
    move_generation = modules["move_generation"]
    move_ordering = modules["move_ordering"]
    search = modules["search"]
    transposition = modules["transposition"]
    tablebase = modules["tablebase"]

    router = APIRouter()


    class FenRequest(BaseModel):
        fen: str
        history: Optional[List[str]] = None


    class EvalRequest(FenRequest):
        ply: Optional[int] = 0
        is_engine_move: Optional[bool] = False


    class MovesRequest(FenRequest):
        moves: Optional[List[str]] = None
        tt_move: Optional[str] = None
        killers: Optional[List[str]] = None


    class SearchRequest(FenRequest):
        max_depth: int = 3
        engine_is_black: bool = True
        bot_id: Optional[str] = None


    def _board_from_request(req: FenRequest) -> chess.Board:
        try:
            board = chess.Board(req.fen)
            for h in req.history or []:
                board.push_san(h)
            return board
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid FEN or history: {e}")


    def _new_request_tt():
        return transposition.TranspositionTable()


    @router.post("/evaluate")
    def evaluate_position(req: EvalRequest):
        board = _board_from_request(req)
        tt = _new_request_tt()
        
        # Run a fast shallow search (depth 2) to resolve tactics, captures, AND mate threats
        _, info_after = search.search_with_info(board, 2, engine_is_black=(board.turn == chess.BLACK), tt=tt)
        score = info_after.get("eval_cp", 0)
        
        explanation = None
        history_list = req.history or []
        if history_list:
            try:
                board_before = chess.Board(req.fen)
                for h in history_list[:-1]:
                    board_before.push_san(h)
                last_move = board_before.parse_san(history_list[-1])
                
                # Evaluate the prev position with the same depth 2 search for an accurate diff
                _, info_before = search.search_with_info(board_before, 2, engine_is_black=(board_before.turn == chess.BLACK), tt=tt)
                prev_eval = info_before.get("eval_cp", 0)
                
                if req.is_engine_move:
                    # Engine move: use dedicated analyzer that explains threats, forks, etc.
                    explanation = explain.analyze_engine_move(board_before, last_move, int(prev_eval), int(score))
                else:
                    # Player move: use existing rule-based analyzer
                    temp_explanation = explain.analyze_move(board_before, last_move, int(prev_eval), int(score), None, False)
                    if temp_explanation and temp_explanation.get("key") in ["BLUNDER", "GREAT_MOVE"]:
                        # Do a very shallow search to find the engine's preferred move for the "Coach"
                        best, _ = search.search_with_info(board_before, 4, engine_is_black=False, tt=tt)
                        best_san = board_before.san(best) if best else None
                        explanation = explain.analyze_move(board_before, last_move, int(prev_eval), int(score), best_san, False)
                    else:
                        explanation = temp_explanation
                    
            except Exception:
                pass

        return {"score_cp": int(score), "explanation": explanation}


    class AnalyzeGameRequest(BaseModel):
        history: List[str]
        player_is_white: Optional[bool] = True

    @router.post("/analyze_game")
    def analyze_game(req: AnalyzeGameRequest):
        """
        Batch-analyze every move in a completed game.
        Returns a per-ply list with eval, annotation, and best_move_san.
        """
        history = req.history
        results = []
        board = chess.Board()  # start from the initial position
        tt = _new_request_tt()

        # Evaluate position before any move (ply 0 baseline)
        _, info0 = search.search_with_info(board, 2, engine_is_black=not req.player_is_white, tt=tt)
        prev_eval = int(info0.get("eval_cp", 0))

        for idx, san in enumerate(history):
            try:
                board_before = board.copy()
                move = board.push_san(san)
                board_after = board.copy()

                is_white_move = board_before.turn == chess.WHITE
                is_player_move = is_white_move if req.player_is_white else not is_white_move

                # Current eval after the move
                _, info_after = search.search_with_info(board_after, 2, engine_is_black=(board_after.turn == chess.BLACK), tt=tt)
                curr_eval = int(info_after.get("eval_cp", 0))

                # Best move from board_before according to engine
                best_move_obj, _ = search.search_with_info(board_before, 3, engine_is_black=(board_before.turn == chess.BLACK), tt=tt)
                best_move_san = board_before.san(best_move_obj) if best_move_obj else None
                best_move_uci = best_move_obj.uci() if best_move_obj else None

                # Eval diff from the perspective of whoever just moved
                if is_white_move:
                    eval_diff = curr_eval - prev_eval
                else:
                    eval_diff = prev_eval - curr_eval

                # Annotation thresholds (only meaningful for player moves)
                if is_player_move:
                    if eval_diff > 200:
                        annotation, symbol, color = "BRILLIANT", "!!", "#f0c040"
                    elif eval_diff > 50:
                        annotation, symbol, color = "GOOD", "!", "#54c481"
                    elif eval_diff >= -50:
                        annotation, symbol, color = "NEUTRAL", "", "#888888"
                    elif eval_diff >= -150:
                        annotation, symbol, color = "INACCURACY", "?!", "#e6bc97"
                    elif eval_diff >= -300:
                        annotation, symbol, color = "MISTAKE", "?", "#e07030"
                    else:
                        annotation, symbol, color = "BLUNDER", "??", "#b43232"
                else:
                    annotation, symbol, color = "ENGINE", "", "#888888"

                # Generate Explanation Text
                explanation_text = None
                if is_player_move:
                    # Use the enhanced analyze_move for base explanation
                    exp_dict = explain.analyze_move(board_before, move, prev_eval, curr_eval, best_move_san, False)
                    if exp_dict and "text" in exp_dict:
                        explanation_text = exp_dict["text"]

                    # For mistakes/blunders, append specific reasoning about the best move
                    if annotation in ["BLUNDER", "MISTAKE", "INACCURACY"] and best_move_obj and best_move_san:
                        best_reason = explain.explain_best_move(
                            board_before, move, best_move_obj, best_move_san, annotation
                        )
                        if best_reason:
                            explanation_text = best_reason  # Use the full best-move explanation
                    
                    # Fallback for great/brilliant moves without an explanation
                    if not explanation_text and annotation in ["BRILLIANT", "GOOD"]:
                        explanation_text = "Strong move — this maintains or improves your advantage."
                else:
                    # Engine move: use the dedicated engine move analyzer
                    eng_dict = explain.analyze_engine_move(board_before, move, prev_eval, curr_eval)
                    if eng_dict and "text" in eng_dict:
                        explanation_text = eng_dict["text"]
                    else:
                        explanation_text = "The engine makes a quiet positional move."

                results.append({
                    "ply": idx + 1,
                    "move": san,
                    "move_uci": move.uci(),
                    "eval_cp": curr_eval,
                    "eval_diff": eval_diff,
                    "annotation": annotation,
                    "annotation_symbol": symbol,
                    "annotation_color": color,
                    "best_move_san": best_move_san,
                    "best_move_uci": best_move_uci,
                    "is_player_move": is_player_move,
                    "explanation_text": explanation_text,
                })

                prev_eval = curr_eval

            except Exception:
                # Skip invalid moves silently
                pass

        return {"analysis": results}


    @router.post("/generate_moves")
    def generate_moves(req: FenRequest):
        board = _board_from_request(req)
        moves = move_generation.generate_legal_moves(board)
        return {"moves": [m.uci() for m in moves]}


    @router.post("/order_moves")
    def order_moves(req: MovesRequest):
        board = _board_from_request(req)

        if not req.moves:
            moves = move_generation.generate_legal_moves(board)
        else:
            try:
                moves = [chess.Move.from_uci(m) for m in req.moves]
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid move in moves list: {e}")

        tt_move = None
        if req.tt_move:
            try:
                tt_move = chess.Move.from_uci(req.tt_move)
            except Exception:
                tt_move = None

        killers_list = None
        if req.killers:
            killers_list = []
            for k in req.killers:
                try:
                    killers_list.append(chess.Move.from_uci(k))
                except Exception:
                    pass

        ordered = move_ordering.order_moves(board, moves, tt_move=tt_move, killers=killers_list)
        return {"ordered_moves": [m.uci() for m in ordered]}


    @router.get("/bots")
    def get_bots():
        return {
            "bots": [
                {"id": "bot1", "name": "Martin (Beginner)", "elo": "800 ELO"},
                {"id": "bot2", "name": "Jimmy (Casual)", "elo": "1200 ELO"},
                {"id": "bot3", "name": "Sven (Intermediate)", "elo": "1500 ELO"},
                {"id": "bot4", "name": "Beth (Advanced)", "elo": "2000 ELO"},
                {"id": "bot5", "name": "Magnus (Expert)", "elo": "2500+ ELO"},
            ]
        }


    @router.post("/search")
    def search_position(req: SearchRequest):
        board = _board_from_request(req)
        tt = _new_request_tt()
        
        depth = req.max_depth
        if req.bot_id is not None:
            bot_depths = {
                "bot1": 3,
                "bot2": 5,
                "bot3": 4,
                "bot4": 7,
                "bot5": 6,
            }
            depth = bot_depths.get(cast(str, req.bot_id), depth)

        move, info = search.search_with_info(board, depth, engine_is_black=req.engine_is_black, tt=tt)


        move_uci = move.uci() if move is not None else None
        info_serializable: Dict[str, Any] = {}
        for k, v in info.items():
            if k == "move":
                info_serializable[k] = v.uci() if v is not None else None
            elif k == "time_ms":
                info_serializable["time_ms"] = int(v)
                info_serializable["time_s"] = f"{int(v) / 1000.0:.2f}"
            elif k == "qnodes":
                info_serializable["q_nodes"] = int(v)
            elif k == "max_qply":
                info_serializable["max_q_ply"] = int(v)
            else:
                try:
                    info_serializable[k] = int(v)
                except Exception:
                    info_serializable[k] = v
        
        return {"best_move": move_uci, "info": info_serializable}


    @router.post("/tt/clear")
    def clear_transposition_table():
        return {
            "cleared": False,
            "message": "Request-local TT is enabled in API search routes; there is no shared cache to clear.",
        }


    @router.get("/tablebase/status")
    def get_tablebase_status():
        is_loaded = tablebase.is_tablebase_loaded()
        return {"loaded": is_loaded}


    @router.post("/tablebase/probe")
    def probe_tablebase(req: FenRequest):
        board = _board_from_request(req)
        if not tablebase.is_tablebase_loaded():
            raise HTTPException(status_code=503, detail="Tablebase not loaded")
        
        wdl = tablebase.probe_wdl(board)
        dtz = tablebase.probe_dtz_no_ep(board)
        best_root_move = tablebase.tablebase_move_for_root(board)
        
        return {
            "wdl": wdl,
            "dtz": dtz,
            "move": best_root_move.uci() if best_root_move else None
        }


    return router
