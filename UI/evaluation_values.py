"""Helpers to normalize engine evaluation outputs into a canonical Python dict.

The engine may return either:
- a tuple from `algorithms.search.iterative_deepening`: (move, value, depth, stats, elapsed_seconds)
- a pair (move, info_dict) or the `info` dict produced by `search_with_info`.

Use `search_result_to_dict(result)` to obtain a stable dict with these keys:
  - move_uci, eval_cp, depth, time_ms, nodes, qnodes, cutoffs,
    tt_hits, tt_probes, max_ply, max_qply

The function returns a Python dict (not a JSON string) as requested.
"""
from typing import Any, Dict
from dataclasses import is_dataclass, asdict

# import SearchStats type for explicit handling
try:
    from algorithms.search import SearchStats
except Exception:
    SearchStats = None


def _to_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _extract_stats_field(stats: Any, name: str, default: int = 0) -> int:
    # stats may be an object with attributes or a dict
    if stats is None:
        return default
    # If it's a dict-like structure
    if isinstance(stats, dict):
        return _to_int(stats.get(name, default), default)

    # If it's a dataclass (SearchStats), convert to dict for robust access
    if is_dataclass(stats):
        try:
            d = asdict(stats)
            return _to_int(d.get(name, default), default)
        except Exception:
            pass

    # explicit type check for SearchStats when import failed above
    if SearchStats is not None and isinstance(stats, SearchStats):
        return _to_int(getattr(stats, name, default), default)

    # fallback: try attribute access
    return _to_int(getattr(stats, name, default), default)


def search_result_to_dict(result: Any) -> Dict[str, Any]:
    """Normalize various engine search outputs into a canonical Python dict.

    Accepted input forms:
    - (move, value, depth, stats, elapsed_seconds)
    - (move, info_dict)
    - info_dict already containing the expected keys

    Returned dict fields:
    - move_uci: str or None
    - eval_cp: int
    - depth: int
    - time_ms: int
    - nodes, qnodes, cutoffs, tt_hits, tt_probes, max_ply, max_qply: ints
    """
    # If caller passed the info dict directly
    if isinstance(result, dict):
        info = result
        move = info.get("move")
        move_uci = None
        try:
            move_uci = move.uci() if move is not None else None
        except Exception:
            move_uci = move if isinstance(move, str) else None

        # info produced by search_with_info already uses these keys; fall back safely
        return {
            "move_uci": move_uci,
            "eval_cp": _to_int(info.get("eval_cp", info.get("value", 0))),
            "depth": _to_int(info.get("depth", 0)),
            "time_ms": _to_int(info.get("time_ms", info.get("elapsed_ms", 0))),
            "nodes": _to_int(info.get("nodes", 0)),
            "qnodes": _to_int(info.get("qnodes", 0)),
            "cutoffs": _to_int(info.get("cutoffs", 0)),
            "tt_hits": _to_int(info.get("tt_hits", 0)),
            "tt_probes": _to_int(info.get("tt_probes", 0)),
            "max_ply": _to_int(info.get("max_ply", 0)),
            "max_qply": _to_int(info.get("max_qply", 0)),
        }

    # If result is a tuple/list
    if isinstance(result, (list, tuple)):
        # common: iterative_deepening returns (move, value, depth, stats, elapsed_seconds)
        if len(result) >= 5:
            move, value, depth, stats, elapsed = result[:5]
            # move -> UCI
            move_uci = None
            try:
                move_uci = move.uci() if move is not None else None
            except Exception:
                move_uci = move if isinstance(move, str) else None

            # elapsed from iterative_deepening is seconds (float) — convert to ms
            try:
                elapsed_ms = int(float(elapsed) * 1000) if elapsed is not None else 0
                # if elapsed already looks like milliseconds (large int), keep it
                if elapsed_ms > 10_000_000:
                    elapsed_ms = int(elapsed)
            except Exception:
                elapsed_ms = 0

            return {
                "move_uci": move_uci,
                "eval_cp": _to_int(value, 0),
                "depth": _to_int(depth, 0),
                "time_ms": elapsed_ms,
                "nodes": _extract_stats_field(stats, "nodes", 0),
                "qnodes": _extract_stats_field(stats, "qnodes", 0),
                "cutoffs": _extract_stats_field(stats, "cutoffs", 0),
                "tt_hits": _extract_stats_field(stats, "tt_hits", 0),
                "tt_probes": _extract_stats_field(stats, "tt_probes", 0),
                "max_ply": _extract_stats_field(stats, "max_ply", 0),
                "max_qply": _extract_stats_field(stats, "max_qply", 0),
            }

        # other form: (move, info_dict) returned by search_with_info caller
        if len(result) == 2 and isinstance(result[1], dict):
            _, info = result
            return search_result_to_dict(info)

    # Unknown / unsupported format
    return {
        "move_uci": None,
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


__all__ = ["search_result_to_dict"]
