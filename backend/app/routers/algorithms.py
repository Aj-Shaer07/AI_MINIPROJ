from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, cast
import chess


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


    @router.post("/evaluate")
    def evaluate_position(req: EvalRequest):
        board = _board_from_request(req)
        score = evaluation.evaluate(board, ply=req.ply)
        return {"score_cp": int(score)}


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
                {"id": "bot1", "name": "Beginner Bot", "elo": "Elo 800"},
                {"id": "bot2", "name": "Casual Bot", "elo": "Elo 1200"},
                {"id": "bot3", "name": "Intermediate Bot", "elo": "Elo 1500"},
                {"id": "bot4", "name": "Advanced Bot", "elo": "Elo 2000"},
                {"id": "bot5", "name": "Expert Bot", "elo": "Elo 2500"},
            ]
        }


    @router.post("/search")
    def search_position(req: SearchRequest):
        board = _board_from_request(req)
        
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

        move, info = search.search_with_info(board, depth, engine_is_black=req.engine_is_black)

        move_uci = move.uci() if move is not None else None
        info_serializable: Dict[str, Any] = {}
        for k, v in info.items():
            if k == "move":
                info_serializable[k] = v.uci() if v is not None else None
            else:
                try:
                    info_serializable[k] = int(v)
                except Exception:
                    info_serializable[k] = v

        return {"best_move": move_uci, "info": info_serializable}


    @router.post("/tt/clear")
    def clear_transposition_table():
        transposition.clear()
        return {"cleared": True}


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
