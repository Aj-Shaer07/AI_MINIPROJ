#!/usr/bin/env python3
"""Analyze CSV produced by collect_search_data.py and print summary metrics.

Usage:
  python3 analyze_search_data.py --in sample.csv
"""
import argparse
import csv


def parse_csv(path):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # convert numeric fields
            for k in ("depth", "nodes", "qnodes", "cutoffs", "tt_hits", "tt_probes", "max_ply", "max_qply", "time_ms", "eval_cp"):
                r[k] = int(r.get(k) or 0)
            r["move_number"] = int(r.get("move_number") or 0)
            rows.append(r)
    return rows


def summarize(rows):
    total_nodes = sum(r["nodes"] for r in rows)
    total_qnodes = sum(r["qnodes"] for r in rows)
    total_moves = len(rows)
    avg_nodes = total_nodes / total_moves if total_moves else 0
    avg_time = sum(r["time_ms"] for r in rows) / total_moves if total_moves else 0
    avg_depth = sum(r["depth"] for r in rows) / total_moves if total_moves else 0
    max_depth = max((r["depth"] for r in rows), default=0)

    # TT hit rate
    total_tt_hits = sum(r["tt_hits"] for r in rows)
    total_tt_probes = sum(r["tt_probes"] for r in rows)
    tt_hit_rate = (total_tt_hits / total_tt_probes) if total_tt_probes else None

    # Cutoff rate
    total_cutoffs = sum(r["cutoffs"] for r in rows)
    cutoff_rate = total_cutoffs / total_nodes if total_nodes else None

    # Effective branching factor estimate per-move (b = nodes^(1/depth))
    b_values = []
    for r in rows:
        d = r["depth"]
        n = r["nodes"]
        if d > 0 and n > 0:
            b_values.append(n ** (1.0 / d))
    avg_b = sum(b_values) / len(b_values) if b_values else None

    return {
        "total_moves": total_moves,
        "total_nodes": total_nodes,
        "total_qnodes": total_qnodes,
        "avg_nodes": avg_nodes,
        "avg_time_ms": avg_time,
        "avg_depth": avg_depth,
        "max_depth": max_depth,
        "tt_hit_rate": tt_hit_rate,
        "cutoff_rate": cutoff_rate,
        "avg_effective_b": avg_b,
    }


def print_summary(s):
    print("Search Analysis Summary:")
    print(f"  Total moves recorded: {s['total_moves']}")
    print(f"  Total nodes searched: {s['total_nodes']}")
    print(f"  Total quiescence nodes: {s['total_qnodes']}")
    print(f"  Average nodes/move: {s['avg_nodes']:.1f}")
    print(f"  Average time/move: {s['avg_time_ms']:.1f} ms")
    print(f"  Average depth reached: {s['avg_depth']:.2f}")
    print(f"  Max depth reached: {s['max_depth']}")
    if s['tt_hit_rate'] is not None:
        print(f"  Transposition table hit rate: {s['tt_hit_rate']:.3f}")
    else:
        print("  Transposition table hit rate: N/A (no probes)")
    if s['cutoff_rate'] is not None:
        print(f"  Cutoff rate (cutoffs/nodes): {s['cutoff_rate']:.6f}")
    else:
        print("  Cutoff rate: N/A")
    if s['avg_effective_b'] is not None:
        print(f"  Avg effective branching factor: {s['avg_effective_b']:.2f}")
    else:
        print("  Avg effective branching factor: N/A")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="infile", required=True)
    args = parser.parse_args()

    rows = parse_csv(args.infile)
    s = summarize(rows)
    print_summary(s)


if __name__ == "__main__":
    main()
