from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import chess


def get_router(modules: Dict[str, Any]) -> APIRouter:
    evaluation = modules["evaluation"]
    move_generation = modules["move_generation"]
    move_ordering = modules["move_ordering"]
    search = modules["search"]
    transposition = modules["transposition"]

    router = APIRouter()


    class FenRequest(BaseModel):
        fen: str


    class EvalRequest(FenRequest):
        ply: Optional[int] = 0


    class MovesRequest(FenRequest):
        moves: Optional[List[str]] = None
        tt_move: Optional[str] = None
        killers: Optional[List[str]] = None


    class SearchRequest(FenRequest):
        max_depth: int = 3
        engine_is_black: bool = True


    def _board_from_fen(fen: str) -> chess.Board:
        try:
            return chess.Board(fen)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid FEN: {e}")


    @router.post("/evaluate")
    def evaluate_position(req: EvalRequest):
        board = _board_from_fen(req.fen)
        score = evaluation.evaluate(board, ply=req.ply)
        return {"score_cp": int(score)}


    @router.post("/generate_moves")
    def generate_moves(req: FenRequest):
        board = _board_from_fen(req.fen)
        moves = move_generation.generate_legal_moves(board)
        return {"moves": [m.uci() for m in moves]}


    @router.post("/order_moves")
    def order_moves(req: MovesRequest):
        board = _board_from_fen(req.fen)

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

        ordered = move_ordering.order_moves(board, moves, tt_move=tt_move)
        return {"ordered_moves": [m.uci() for m in ordered]}


    @router.post("/search")
    def search_position(req: SearchRequest):
        board = _board_from_fen(req.fen)
        move, info = search.search_with_info(board, req.max_depth, engine_is_black=req.engine_is_black)

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


    return router
