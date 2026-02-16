#!/usr/bin/env python3
"""Play engine vs engine and record per-move search stats to CSV.

Place this file at the project root and run like:
  python3 collect_search_data.py --games 1 --depth 3 --out sample.csv
"""
import argparse
import csv
import chess
from datetime import datetime
import sys
import os

# Ensure the algorithms package modules can be imported as top-level modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "algorithms"))
from algorithms.search import search_with_info


def play_game(max_depth, out_writer):
    board = chess.Board()
    move_number = 1

    while not board.is_game_over() and move_number <= 200:
        move, info = search_with_info(board, max_depth, engine_is_black=(not board.turn))
        if move is None:
            break

        row = {
            "timestamp": datetime.utcnow().isoformat(),
            "move_number": move_number,
            "side": "black" if not board.turn else "white",
            "move_uci": move.uci(),
            "fen": board.fen(),
            "depth": info.get("depth"),
            "nodes": info.get("nodes"),
            "qnodes": info.get("qnodes"),
            "cutoffs": info.get("cutoffs"),
            "tt_hits": info.get("tt_hits"),
            "tt_probes": info.get("tt_probes"),
            "max_ply": info.get("max_ply"),
            "max_qply": info.get("max_qply"),
            "time_ms": info.get("time_ms"),
            "eval_cp": info.get("eval_cp"),
        }
        out_writer.writerow(row)

        board.push(move)
        move_number += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=1)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--out", type=str, default="search_data.csv")
    args = parser.parse_args()

    fieldnames = [
        "timestamp",
        "move_number",
        "side",
        "move_uci",
        "fen",
        "depth",
        "nodes",
        "qnodes",
        "cutoffs",
        "tt_hits",
        "tt_probes",
        "max_ply",
        "max_qply",
        "time_ms",
        "eval_cp",
    ]

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for g in range(args.games):
            play_game(args.depth, writer)

    print(f"Wrote data to {args.out}")


if __name__ == "__main__":
    main()
