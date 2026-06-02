# Chess AI — Frontend

> React + TypeScript single-page application built with Vite.

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

Opens at http://localhost:5173

## Pages

| Page | Route | Description |
|------|-------|-------------|
| **Landing** | `/` | 3-step wizard: Hero → Game Settings → Bot Selection (5 bots with emoji avatars, ELO, depth) |
| **Game** | `/game` | Main gameplay — interactive chessboard, engine eval bar, move list, clock, coach mode popups, promotion overlay, game-over overlay |
| **Analysis** | `/analysis` | Post-game review — eval graph (SVG), annotated move list (‼/!/⁈/?/?? symbols), best-move arrow overlay, keyboard navigation |
| **Arena** | `/arena` | Adaptive difficulty hub — ELO badge, 5×4 ELO ladder grid, win/loss/draw record, collapsible settings, calibration system |

## Component Hierarchy

```
App
├── Header (brand link)
└── Routes
    ├── Landing
    │   ├── Hero (Step 0) — preview board, Arena teaser
    │   ├── Settings (Step 1) — time/color/clock/coach
    │   └── Bot Selection (Step 2) — 5 bot cards
    ├── Game
    │   ├── EvaluationBar
    │   ├── Chessboard → Square (×64) + Arrow SVG
    │   ├── Panel (move list + resign)
    │   ├── ExplainPopup (coach mode)
    │   ├── CapturedBar
    │   └── Game Over Overlay
    ├── Analysis
    │   ├── EvalGraph (pure SVG, no charting library)
    │   ├── Chessboard (read-only + best-move arrow)
    │   └── AnnotatedMoveList
    └── Arena
        ├── ELO Badge + Stats
        ├── ELO Ladder Grid (5×4)
        └── Settings Panel
```

## State Management

All game logic lives in the `useGameController` custom hook:

- **Source of truth**: `chess.js` `Chess` instance in a `useRef` (no re-renders on internal state changes)
- **Move history**: Stored in a `useRef` to prevent stale closures in async callbacks
- **Display state**: Derived values in `useState` — board, lastMove, evalCp, turn, clocks, gameOver, etc.
- **Clock**: `setInterval` at 100ms, decrements active player's time
- **Engine turns**: Async API call to `/search` or `/arena/search`, then applies response
- **Premove system**: Queued move stored in both ref (async access) and state (UI display)

## API Integration

All backend calls go through `utils/api.ts`:
- Base URL: `http://localhost:8000`
- Arena session ID: UUID via `crypto.randomUUID()`, persisted in `localStorage`
- Sent as `X-Session-Id` header for all `/arena/*` endpoints

## Tech Stack

- React 19 + TypeScript
- Vite 7
- React Router 6
- chess.js (client-side move validation)
- Pure SVG for eval graphs (no charting library)
