# Chess Engine – Minimax with Alpha-Beta Pruning

## Project Workflow

1. **Requirement Analysis**
   - Get a basic UI working (in progress)
   - Define the evaluation function / evaluation metric 

2. **Upgrade to Architecture Planning**
   - Design engine structure (board representation, move generation, search, evaluation) (done basic)

3. **Review of Search & Evaluation Strategy**
   - Review minimax algorithm with alpha-beta pruning 
   - Evaluate pruning efficiency and depth handling 

4. **Get a Basic Engine Working**
   - Implement move generation (done)
   - Implement minimax with alpha-beta pruning (done)
   - Connect evaluation function

5. **Data / Heuristic Improvement & Self-Play**
   - Improve evaluation heuristics
   - Use self-play games for testing and tuning

## --------------------MIDSEM EVAL----------------------

6. **Hyperparameter Tuning & Performance Optimization**
   - Deep Learning
   - Search depth
   - Move ordering
   - Pruning parameters

7. **Engine Optimization**
   - Make the engine faster
   - Increase number of nodes searched
   - Test performance at different ELO levels

8. **Performance Comparison**
   - Compare different engine versions
   - Run round-robin matches against other engines
   - Compare results using evaluation metrics (win rate, ELO, nodes/sec)

## --------------------ENDSEM EVAL----------------------

---

## Algorithm Summary

This project implements a full-strength chess engine in both **Python** (`algorithms/`) and **Dart** (`mindgambit/lib/engine/`). Both versions are kept in sync and implement identical chess logic.

---

### Evaluation (`evaluation.py` / `evaluation.dart`)

#### Material Values (PeSTO-style Tapered Eval)
Two sets of material values are maintained — **midgame (MG)** and **endgame (EG)** — and blended based on game phase:

| Piece | MG Value | EG Value |
|-------|----------|----------|
| Pawn | 82 | 94 |
| Knight | 337 | 281 |
| Bishop | 365 | 297 |
| Rook | 477 | 512 |
| Queen | 1025 | 936 |

Game phase is computed from remaining minor/major pieces (max 24 at game start). Score = `(mg_score × phase + eg_score × (24 − phase)) / 24`.

#### Piece-Square Tables (PeSTO)
Full 64-square midgame and endgame PSTs for all six piece types (sourced from PeSTO). Tables are stored rank-1-first; Black pieces are mirrored (`sq ^ 56`).

#### Pawn Structure
- **Doubled pawns**: −15 EG per extra pawn on the same file.
- **Isolated pawns**: −20 MG/EG for pawns with no friendly pawn on adjacent files.
- **Passed pawns**: bonus scaled by effective rank (MG: 5–100 cp, EG: 15–250 cp).
  - **Rook behind passer**: +40 EG when a friendly rook is on the same file behind the passer.
  - **Connected passers**: +30 EG when two passed pawns are on adjacent files.
  - **King proximity**: EG bonus proportional to how close the friendly king is and how far the enemy king is (for advanced passers only, rank ≥ 3).

#### Piece Bonuses
- **Bishop pair**: +30 MG/EG.
- **Rook on open file**: +25 MG/EG.
- **Rook on semi-open file**: +12 MG/EG.
- **King pawn shield**: +10 MG per shielding pawn (active only when phase > 6).
- **Hanging piece penalty**: −50% of piece value when a non-pawn piece is attacked but undefended.

#### Endgame Patterns
- **Mop-up**: when ahead by ≥200 cp, rewards pushing the losing king to the edge (+15 × edge distance) and keeping the winning king close (+8 × proximity).
- **K+B+B vs K**: additional bonus driving the losing king towards any corner (×20 per unit closer).
- **K+B+N vs K**: strongest guidance — drives the losing king to the corner matching the bishop's square colour (×40 per unit closer + ×10 for king proximity).
- **Stalemate avoidance**: when the losing side has ≤ 2 legal moves and we hold a large material advantage, apply a penalty to avoid accidental stalemate.
- **50-move rule decay**: when halfmove clock > 30, linearly reduce the winning side's score to encourage decisive progress.

---

### Search (`search.py` / `search.dart`)

#### Core Algorithm
- **Negamax** with **alpha-beta pruning** (fail-soft).
- **Iterative deepening**: searches depth 1 → max_depth, reusing killer/history tables across iterations.
- **Quiescence search**: extends leaf nodes with capture-only search (+ all moves in check) to resolve tactical sequences before returning a static evaluation.

#### Search Enhancements
| Enhancement | Description |
|---|---|
| **Aspiration windows** | ±50 cp window around previous iteration score; full re-search on fail |
| **Transposition table (TT)** | Depth-preferred replacement, up to ~1 M entries; exact / lower / upper bound probing |
| **Principal Variation Search (PVS)** | Zero-window scout search for non-first moves; re-search only on fail-high |
| **Late Move Reductions (LMR)** | Reduce depth by 1 (moves 4–5) or 2 (moves 6+) for quiet, non-check moves |
| **Check extensions** | Extend depth by 1 when giving check, up to 3 times per line |
| **Null-move pruning** | Python only (Dart chess package doesn't expose null moves) |
| **Killer heuristic** | Remember 2 quiet moves per ply that caused a beta cutoff |
| **History heuristic** | Accumulate `depth²` bonus for quiet moves that raise alpha |
| **Endgame depth boost** | Automatically increase depth by +1/+2/+3 when ≤16/10/6 pieces remain |
| **Time limit** | Dart: 5 s hard cutoff; checked every 1024 nodes |

#### Opening Book (Dart — expanded)
Instant replies for the first 4 half-moves (2 full moves each side), covering 1.e4 e5, Sicilian, 1.d4 d5 / Nf6, Queen's Gambit, English, and Réti.

---

### Move Ordering (`move_ordering.py` / `move_ordering.dart`)

Moves are scored and sorted highest-first before each alpha-beta node:

| Priority | Score | Condition |
|----------|-------|-----------|
| 1 | 10 000 | TT (hash) move |
| 2 | 1 000 – 8 900 | Capture (MVV-LVA): 10×victim_value − attacker_value |
| 3 | 9 000 | Queen promotion |
| 4 | 3 000 | Knight promotion (tactical) |
| 5 | 1 000 | En passant |
| 6 | 800 | Killer move (quiet, caused cutoff) |
| 7 | 0 – 700 | History heuristic (capped to not override killers) |

---

### Transposition Table (`transposition.py` / `transposition.dart`)

- **Storage**: FEN string → `(depth, score, flag, best_move)`.
- **Replacement**: depth-preferred — only replace if new search depth ≥ existing entry.
- **Bounds flags**: EXACT (score is the true value), LOWER (fail-high / beta cutoff), UPPER (fail-low / did not improve alpha).
- **Size limit**: ~1 M entries; oldest 25% evicted when exceeded.

---

### Python vs Dart Parity

| Feature | Python | Dart |
|---|:---:|:---:|
| PeSTO PSTs | ✅ | ✅ |
| Tapered eval | ✅ | ✅ |
| Pawn structure (doubled/isolated/passed) | ✅ | ✅ |
| Rook behind passer | ✅ | ✅ |
| Connected passers | ✅ | ✅ |
| King proximity to passer | ✅ | ✅ |
| Bishop pair / Hanging piece / Open file | ✅ | ✅ |
| King shield | ✅ | ✅ |
| Mop-up + K+BB + K+BN endgames | ✅ | ✅ |
| Stalemate avoidance | ✅ | ✅ |
| 50-move rule decay | ✅ | ✅ |
| Negamax + alpha-beta | ✅ | ✅ |
| Iterative deepening + aspiration windows | ✅ | ✅ |
| Quiescence search + delta pruning | ✅ | ✅ |
| PVS | ✅ | ✅ |
| LMR | ✅ | ✅ |
| Check extensions | ✅ | ✅ |
| Null-move pruning | ✅ | ❌ (package limitation) |
| Killer + history heuristics | ✅ | ✅ |
| Transposition table | ✅ | ✅ |
| Endgame depth boost | ✅ | ✅ |
| Time limit | ❌ | ✅ (5 s) |
| Opening book | ✅ (2 ply) | ✅ (4 ply) |
