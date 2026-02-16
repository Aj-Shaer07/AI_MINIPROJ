# Chess Engine – Algorithms Methodology

## 1. Overview

This chess engine is built in Python using the `python-chess` library for board representation and legal move generation. The AI decision-making is handled by a collection of modules in the `algorithms/` package, each responsible for a distinct aspect of the engine's play. The architecture follows the classical approach used by competitive chess programs: **search** (finding the best move), **evaluation** (scoring positions), **move ordering** (optimizing search efficiency), and **transposition tables** (caching previously computed results).

---

## 2. Module-by-Module Methodology

### 2.1 Move Generation (`move_generation.py`)

**Purpose:** Provides a clean interface for generating all legal moves in a given position.

**Method:** Wraps `python-chess`'s built-in `board.legal_moves` generator into a list. The `python-chess` library handles all rules including castling, en passant, pawn promotion, and pinned-piece legality.

```python
def generate_legal_moves(board):
    return list(board.legal_moves)
```

This abstracts the move generation behind a function boundary so the search module is not directly coupled to the `python-chess` API.

---

### 2.2 Evaluation (`evaluation.py`)

**Purpose:** Assigns a numerical score (in centipawns) to any board position. Positive scores favor White; negative scores favor Black.

The evaluation function combines **multiple heuristic features**, each contributing to the overall positional assessment. The evaluation is split into **midgame** and **endgame** components, which are blended using a **tapered evaluation** scheme.

#### 2.2.1 Material Counting

Each piece is assigned separate midgame (MG) and endgame (EG) values:

| Piece  | MG Value | EG Value |
|--------|----------|----------|
| Pawn   | 82       | 94       |
| Knight | 337      | 281      |
| Bishop | 365      | 297      |
| Rook   | 477      | 512      |
| Queen  | 1025     | 936      |

The values follow modern tuned ratios (knights slightly lower than bishops, rook values increase in endgames).

#### 2.2.2 Piece-Square Tables (PeSTO)

**Source:** PeSTO's Evaluation Function (chessprogramming.org)

Each piece type has a 64-element lookup table for both MG and EG phases. These tables encode positional knowledge:
- **Pawns:** Reward central advancement, penalize edge pawns.
- **Knights:** Reward central outposts, penalize rim/corner placement.
- **Bishops:** Reward long diagonals, penalize being trapped.
- **Rooks:** Reward 7th-rank placement, penalize being passive.
- **Queens:** Cautious development in MG, centralization in EG.
- **Kings:** Safety behind pawns in MG, centralization in EG.

Tables are stored from White's perspective and mirrored for Black using `_mirror(sq) = sq ^ 56` (rank flip).

#### 2.2.3 Tapered Evaluation (Game-Phase Blending)

A **phase score** is computed based on remaining pieces (Knights=1, Bishops=1, Rooks=2, Queens=4, total=24 at start):

```
score = (mg_score × phase + eg_score × (24 − phase)) / 24
```

This ensures smooth transitions from opening/middlegame values to endgame values as pieces are traded.

#### 2.2.4 Pawn Structure

| Feature | Bonus/Penalty |
|---------|---------------|
| Doubled Pawns | −15 cp per extra pawn on same file |
| Isolated Pawns | −20 cp (no friendly pawns on adjacent files) |
| Passed Pawns (MG) | 5–100 cp (rank-dependent, rising toward promotion) |
| Passed Pawns (EG) | 15–250 cp (much stronger in endgames) |
| Connected Passed Pawns | +30 cp (adjacent passed pawns support each other) |
| Rook Behind Passer | +40 cp (rook on same file, behind own passed pawn) |

**Passed pawn detection:** A pawn is passed if no enemy pawn can block or capture it on its file or adjacent files in front of it.

**King proximity to passed pawns:** In endgames, the engine rewards the winning king being close to passed pawns and penalizes the opponent's king being far from them.

#### 2.2.5 Piece Activity

- **Bishop Pair Bonus:** +30 cp for having both bishops (compensates for pawn structure weaknesses).
- **Rook on Open File:** +25 cp (no pawns on file) or +12 cp (semi-open, only enemy pawns).
- **Hanging Pieces:** Pieces attacked but not defended are penalized at 50% of their value.

#### 2.2.6 King Safety

- **Pawn Shield:** +10 cp for each pawn directly in front of the castled king (files adjacent to king, one rank ahead).

#### 2.2.7 Endgame-Specific Evaluation

Applied **after** the tapered evaluation for full-strength impact:

**Mop-Up Evaluation (material advantage ≥ 200 cp):**
- Rewards pushing the losing king toward the board edge.
- Rewards keeping the winning king close to the losing king.
- Bonuses scale with the size of the material advantage.

**Specialized Endgame Patterns:**
- **K+B+B vs K:** Drives the losing king to any corner (opposite-colored bishops can checkmate in any corner).
- **K+B+N vs K:** Drives the losing king to the corner matching the bishop's square color (dark-square bishop → a1/h8; light-square bishop → a8/h1).

**Stalemate Avoidance:** When the winning side has ≥200 cp advantage and the losing side has ≤2 legal moves, a penalty is applied to avoid accidental stalemate.

**50-Move Rule Awareness:** As the halfmove clock approaches 50, the winning side's score is gradually decayed to encourage decisive play before a draw is claimed.

---

### 2.3 Move Ordering (`move_ordering.py`)

**Purpose:** Sort moves so the best candidates are searched first, maximizing alpha-beta pruning efficiency.

**Method:** Each move is given a priority score, and the list is sorted in descending order:

| Priority | Move Type | Score |
|----------|-----------|-------|
| 1 | Transposition Table (TT) move | 10,000 |
| 2 | Queen promotions | 9,000 |
| 3 | Knight underpromotions | 3,000 |
| 4 | Winning captures (MVV-LVA) | 1,000+ |
| 5 | En passant captures | 1,000 |
| 6 | Killer moves | 800 |
| 7 | History heuristic moves | 0–700 |
| 8 | Other quiet moves | 0 |

**MVV-LVA (Most Valuable Victim – Least Valuable Attacker):**
```
score = 10 × victim_value − attacker_value
```
This prioritizes capturing high-value pieces with low-value pieces (e.g., pawn takes queen).

**Killer Moves:** Quiet moves that caused a beta cutoff at the same ply in a sibling node. Two killers are stored per ply.

**History Heuristic:** Quiet moves that improved alpha accumulate a score of `depth²`, building a learning table across the search. Capped at 700 so it never overrides killers.

---

### 2.4 Transposition Table (`transposition.py`)

**Purpose:** Cache previously evaluated positions to avoid redundant computation.

**Method:** A Python dictionary mapping position hashes to `(depth, score, flag, best_move)` entries.

**Key Features:**

| Feature | Implementation |
|---------|---------------|
| Hashing | `board.transposition_key()` (Zobrist hash) with fallback to `(board_fen, turn)` |
| Size Limit | 2²⁰ = 1,048,576 entries |
| Replacement | Depth-preferred (deeper entries are kept) |
| Eviction | When full, removes ~25% oldest entries |
| Score Types | **EXACT** (= exact score), **LOWER** (≥ beta, fail-high), **UPPER** (≤ alpha, fail-low) |

**Lookup Logic:**
1. If the stored depth ≥ requested depth:
   - EXACT → return score directly.
   - LOWER and score ≥ beta → return score (beta cutoff).
   - UPPER and score ≤ alpha → return score (fail-low cutoff).
2. Even if score is unusable, the stored **best move** is retrieved for move ordering (TT move priority).

---

### 2.5 Search (`search.py`)

**Purpose:** Find the best move by exploring the game tree. This is the core AI module.

#### 2.5.1 Negamax Algorithm

The search uses the **Negamax** framework, a simplification of Minimax where both sides maximize from their perspective:

```
score(position) = −score(opponent's position)
```

#### 2.5.2 Alpha-Beta Pruning

Maintains a window `[alpha, beta]` representing the range of scores the side to move can guarantee. Branches that fall outside this window are **pruned** (not explored), dramatically reducing the search tree:

- **Alpha:** Best score the maximizing player can guarantee.
- **Beta:** Best score the minimizing player can guarantee.
- **Cutoff:** When `alpha ≥ beta`, remaining moves are skipped.

#### 2.5.3 Iterative Deepening

Instead of searching directly to depth N, the engine searches depth 1, then depth 2, ..., up to depth N. Benefits:

- **Time Management:** Can return a result at any depth if time runs out.
- **Move Ordering:** Each iteration's best move becomes the TT move for the next iteration, improving ordering.

**Endgame Depth Boost:** When few pieces remain (lower branching factor), the maximum depth is automatically increased:
- ≤6 pieces → +3 depth
- ≤10 pieces → +2 depth
- ≤16 pieces → +1 depth

#### 2.5.4 Aspiration Windows

From depth 3 onward, the search starts with a **narrow window** around the previous iteration's score (±50 cp). If the result falls outside this window, a full-width re-search is performed. This typically saves ~10–20% of nodes.

#### 2.5.5 Principal Variation Search (PVS)

After searching the first (presumably best) move with a full window, subsequent moves are searched with a **zero-window** `[alpha, alpha+1]`. If this scout search fails high, a full re-search confirms the result. This exploits the fact that in well-ordered move lists, the first move is usually best.

#### 2.5.6 Null-Move Pruning

Before searching any moves, the engine tries "doing nothing" (passing the turn) with a reduced depth search (depth − 3). If even skipping a turn gives a score ≥ beta, the position is so good that no further search is needed.

**Safeguards:** Null-move pruning is disabled:
- When in check
- At the root node
- At depths < 3
- When the side to move has no non-pawn material (zugzwang risk)

#### 2.5.7 Late Move Reductions (LMR)

After the first few moves have been searched at full depth, later (less promising) quiet moves are searched with **reduced depth**:
- Moves 5–5: reduction of 1 ply
- Moves 6+: reduction of 2 plies

If a reduced search surprisingly improves alpha, a full-depth re-search is performed.

**Excluded from reduction:** Captures, promotions, moves giving check, and moves while in check.

#### 2.5.8 Check Extensions

When a move gives check, the search depth is **not decremented**, allowing the engine to see the full consequences of checks. Limited to a maximum of 3 extensions per branch to prevent search explosion.

#### 2.5.9 Quiescence Search

At leaf nodes (depth = 0), instead of returning a static evaluation, the engine continues searching **only captures** (and all moves when in check) until a "quiet" position is reached. This prevents the horizon effect — misevalauting positions where a piece is about to be captured.

**Delta Pruning:** If the static evaluation plus 1000 cp plus a margin of 200 cp is still below alpha, the remaining captures cannot improve the position and are skipped.

#### 2.5.10 Opening Book

A hardcoded opening book provides instant responses for specific opening moves:
- Against `1. e4` → play `1... e5`
- Against `1. d4` → play `1... d5`

This avoids spending computation time on well-known opening theory.

---

### 2.6 Terminal Interface (`main.py`)

Provides a text-based interface for playing against the engine in the terminal:
- Displays the board state after each move
- Accepts human input in Standard Algebraic Notation (SAN)
- Shows search statistics (depth, eval, time, node count)
- Detects game-over conditions (checkmate, stalemate, draws)

---

### 2.7 Testing (`test_engine.py`)

The automated test suite validates engine correctness across four categories:

| Test Category | Method | Pass Criteria |
|---------------|--------|---------------|
| **Tactical Puzzles** | Sets up known positions (back-rank mate, knight fork, discovery attack) and checks if the engine finds the correct move | ≥ 3/5 puzzles solved |
| **Self-Play vs Random** | Engine plays 3 games against a random mover (max 150 moves each) | ≥ 2/3 wins for the engine |
| **Regression Test** | Searches the standard starting position at depth 4 and verifies it completes without errors | Completes without crash |
| **Endgame Conversion** | Tests K+R vs K, K+Q vs K, and K+R+3P vs K+R for the engine's ability to convert winning endgames via self-play | ≥ 2/3 endgames converted |

---

## 3. Algorithm Flow Diagram

```
┌─────────────────────────────────────────┐
│            Game Start                    │
│    (Starting position or custom FEN)     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│         Opening Book Check               │
│  (Hardcoded responses for 1.e4 / 1.d4)  │
└──────────────┬───────────────────────────┘
               │ Not in book
               ▼
┌──────────────────────────────────────────┐
│       Iterative Deepening                │
│   Depth 1 → 2 → 3 → ... → max_depth    │
│   (with endgame depth boost)             │
│                                          │
│   ┌──────────────────────────────────┐   │
│   │    Aspiration Window             │   │
│   │    ±50 cp around prev score      │   │
│   └──────────┬───────────────────────┘   │
│              │                           │
│              ▼                           │
│   ┌──────────────────────────────────┐   │
│   │    Negamax + Alpha-Beta          │   │
│   │                                  │   │
│   │  ┌────────────────────────────┐  │   │
│   │  │  TT Probe                  │  │   │
│   │  │  Null-Move Pruning         │  │   │
│   │  │  Move Generation + Ordering│  │   │
│   │  │  PVS + LMR                 │  │   │
│   │  │  Check Extensions          │  │   │
│   │  │  Killer / History Updates  │  │   │
│   │  │  TT Store                  │  │   │
│   │  └────────────────────────────┘  │   │
│   │              │                   │   │
│   │              ▼ (depth = 0)       │   │
│   │  ┌────────────────────────────┐  │   │
│   │  │  Quiescence Search         │  │   │
│   │  │  (captures only + checks)  │  │   │
│   │  │  Delta Pruning             │  │   │
│   │  └────────────┬───────────────┘  │   │
│   │               │                  │   │
│   │               ▼                  │   │
│   │  ┌────────────────────────────┐  │   │
│   │  │  Static Evaluation         │  │   │
│   │  │  Material + PST + Pawns    │  │   │
│   │  │  + Activity + King Safety  │  │   │
│   │  │  + Endgame Specializations │  │   │
│   │  └────────────────────────────┘  │   │
│   └──────────────────────────────────┘   │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│         Best Move Returned               │
│   (with eval, depth, stats, time)        │
└──────────────────────────────────────────┘
```

---

## 4. Summary of Techniques

| Technique | Module | Purpose |
|-----------|--------|---------|
| Negamax + Alpha-Beta | `search.py` | Core tree search with pruning |
| Iterative Deepening | `search.py` | Progressive deepening with time safety |
| Aspiration Windows | `search.py` | Narrow search window for efficiency |
| Principal Variation Search | `search.py` | Zero-window probing of non-PV moves |
| Null-Move Pruning | `search.py` | Skip turn to detect overwhelming positions |
| Late Move Reductions | `search.py` | Reduced-depth search for unlikely moves |
| Check Extensions | `search.py` | Extend search when checks are given |
| Quiescence Search | `search.py` | Resolve tactical sequences at leaf nodes |
| Delta Pruning | `search.py` | Skip hopeless captures in quiescence |
| Transposition Table | `transposition.py` | Cache and reuse position evaluations |
| MVV-LVA Ordering | `move_ordering.py` | Prioritize high-value captures |
| Killer Heuristic | `move_ordering.py` | Remember quiet moves that caused cutoffs |
| History Heuristic | `move_ordering.py` | Learn which quiet moves tend to be good |
| PeSTO PST | `evaluation.py` | Positional scoring via lookup tables |
| Tapered Evaluation | `evaluation.py` | Smooth MG-to-EG transition |
| Pawn Structure Analysis | `evaluation.py` | Doubled/isolated/passed pawn evaluation |
| Mop-Up Evaluation | `evaluation.py` | Drive losing king to edge in endgames |
| KBB/KBN Corner Driving | `evaluation.py` | Specialized endgame checkmate patterns |
| Opening Book | `search.py` | Hardcoded replies for common openings |
