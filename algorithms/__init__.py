"""
algorithms — Custom Chess Engine Package
========================================
Core modules for the chess engine:

- **search**:         Negamax with alpha-beta, PVS, LMR, null-move pruning,
                      quiescence search, aspiration windows, iterative deepening
- **evaluation**:     PeSTO-style tapered evaluation with 803 tunable parameters
- **transposition**:  Zobrist-hash transposition table (2^20 entries, depth-preferred)
- **move_ordering**:  MVV-LVA, killer moves, history heuristic
- **openingbook**:    Polyglot opening book integration
- **tablebase**:      Syzygy endgame tablebase probing (≤5 pieces)
- **texel_tuning**:   Automated parameter optimization via L-BFGS-B
- **benchmark**:      Self-play ELO benchmarking harness
"""
