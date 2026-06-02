# Chess AI — Backend

> FastAPI REST API that exposes the custom chess engine to the frontend.

## Architecture

The backend follows a **modular plugin pattern**:
- Algorithm modules (`evaluation`, `search`, `move_ordering`, `transposition`, `tablebase`) are loaded once at startup via `import_algorithms.py`
- Modules are injected into router factories (`get_router(modules)`, `get_arena_router(modules)`)
- Each API request creates a **fresh TranspositionTable** — no shared mutable state between requests (except Arena sessions)

## Quick Start

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Swagger docs: http://127.0.0.1:8000/docs

## API Endpoints

### Core Engine
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/bots` | Returns 5 bot configurations (name, ELO, depth) |
| POST | `/search` | Find best move — accepts `{fen, history, max_depth, engine_is_black, bot_id}` |
| POST | `/evaluate` | Evaluate position — returns `score_cp` + optional coach explanation |
| POST | `/generate_moves` | List all legal moves in UCI format |
| POST | `/order_moves` | Order moves using heuristics (TT, killers, MVV-LVA, history) |
| POST | `/analyze_game` | Batch analyze a completed game — per-ply eval, annotation, best move, explanation |
| POST | `/tt/clear` | Clear transposition table |

### Tablebases
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tablebase/status` | Check if Syzygy tablebases are loaded |
| POST | `/tablebase/probe` | Probe WDL/DTZ for a position (≤5 pieces) |

### Arena (Adaptive Difficulty)
| Method | Endpoint | Description | Header |
|--------|----------|-------------|--------|
| GET | `/arena/session` | Get current session state | `X-Session-Id` |
| POST | `/arena/search` | Search with quality-tier suboptimal move selection | `X-Session-Id` |
| POST | `/arena/result` | Report game result, triggers ELO adjustment | `X-Session-Id` |
| POST | `/arena/reset` | Reset session to baseline | `X-Session-Id` |

## Key Design Decisions

- **Stateless per request**: Each search request creates its own TT — no cross-request cache leakage
- **Arena sessions are in-memory**: Keyed by `X-Session-Id` header (UUID from client localStorage), thread-safe with `threading.Lock`
- **Coach mode**: `/evaluate` uses depth-2 search for low-latency real-time eval; `/analyze_game` uses deeper search for accuracy
- **Bot depth overrides**: Each bot ID maps to a specific search depth, overriding the `max_depth` parameter

## Dependencies

- `fastapi>=0.95.0`
- `uvicorn[standard]>=0.22.0`
- `python-chess>=1.999`
