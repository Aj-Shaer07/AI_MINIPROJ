import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom'
import { Chess } from 'chess.js'
import { analyzeGame } from '../utils/api'
import type { AnalysisPly } from '../utils/api'
import EvalGraph from '../components/EvalGraph'
import AnnotatedMoveList from '../components/AnnotatedMoveList'
import Chessboard from '../components/Chessboard'

type BoardState = string[][]

const fenToBoard = (fen: string): BoardState => {
  const [placement] = fen.split(' ')
  return placement.split('/').map(row => {
    const cells: string[] = []
    for (const ch of row) {
      const n = parseInt(ch)
      if (!isNaN(n)) for (let i = 0; i < n; i++) cells.push('')
      else cells.push(ch)
    }
    return cells
  })
}

// Compute board + lastMove at a given ply (0 = starting position)
function boardAtPly(history: string[], ply: number) {
  const g = new Chess()
  let lastMove: [number, number, number, number] | null = null
  const moves = history.slice(0, ply)
  for (const san of moves) {
    const sq = (s: string): [number, number] => [8 - parseInt(s[1]), s.charCodeAt(0) - 97]
    try {
      const m = g.move(san)
      if (m) {
        const f = sq(m.from)
        const t = sq(m.to)
        lastMove = [f[0], f[1], t[0], t[1]]
      }
    } catch { break }
  }
  return { board: fenToBoard(g.fen()), lastMove }
}

// Convert a UCI move string to [fromRow, fromCol, toRow, toCol]
function uciToCoords(uci: string): [number, number, number, number] | null {
  if (!uci || uci.length < 4) return null
  const fc = uci.charCodeAt(0) - 97
  const fr = 8 - parseInt(uci[1])
  const tc = uci.charCodeAt(2) - 97
  const tr = 8 - parseInt(uci[3])
  return [fr, fc, tr, tc]
}

export default function Analysis() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()

  const state = (location.state as any) || {}
  const history = state.history || []
  
  // Try to get playerColor from searchParams first, then fall back to location.state, then 'white'
  const playerColor = searchParams.get('color') || state.playerColor || 'white'
  const playerIsWhite = playerColor === 'white'
  const totalPlies = history.length

  const [analysis, setAnalysis] = useState<AnalysisPly[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentPly, setCurrentPly] = useState(totalPlies) // start at end of game

  // Derived board state
  const { board, lastMove } = boardAtPly(history, currentPly)

  // Fetch analysis on mount
  useEffect(() => {
    if (!history.length) { setLoading(false); return }
    analyzeGame(history, playerIsWhite)
      .then(res => { setAnalysis(res.analysis); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [])

  // Navigation handlers
  const goTo = useCallback((ply: number) => {
    setCurrentPly(Math.max(0, Math.min(totalPlies, ply)))
  }, [totalPlies])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') goTo(currentPly - 1)
      if (e.key === 'ArrowRight') goTo(currentPly + 1)
      if (e.key === 'Home') goTo(0)
      if (e.key === 'End') goTo(totalPlies)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [currentPly, goTo])

  // Best-move arrow for the current position
  const currentPlyData = analysis.find(p => p.ply === currentPly)
  const played_uci = currentPlyData?.move_uci
  const best_uci = currentPlyData?.best_move_uci
  const showBestArrow = best_uci && played_uci && best_uci !== played_uci
  const bestArrow = showBestArrow ? uciToCoords(best_uci!) : null

  // Evals for the graph
  const evals = analysis.map(p => p.eval_cp)

  if (!history.length) {
    return (
      <div className="analysis-page">
        <div className="analysis-empty">
          <h2>No game data found.</h2>
          <button className="btn btn-primary" onClick={() => navigate('/')}>New Game</button>
        </div>
      </div>
    )
  }

  return (
    <div className="analysis-page">
      {/* Header */}
      <div className="analysis-header">
        <button className="btn btn-outline" onClick={() => navigate('/')}>← New Game</button>
        <h1 className="analysis-title">Post-Game Analysis</h1>
        <span className="analysis-meta">{totalPlies} moves played</span>
      </div>

      {loading ? (
        <div className="analysis-loading">
          <div className="analysis-spinner" />
          <p>Analysing {totalPlies} moves… this may take a moment.</p>
        </div>
      ) : error ? (
        <div className="analysis-error">
          <p>Failed to load analysis: {error}</p>
          <button className="btn btn-primary" onClick={() => navigate('/')}>New Game</button>
        </div>
      ) : (
        <div className="analysis-layout">

          {/* Left: Eval Graph */}
          <aside className="analysis-left">
            <div className="analysis-panel-title">Evaluation</div>
            <div className="eval-graph-wrap">
              <EvalGraph evals={evals} currentPly={currentPly} onPlyClick={goTo} />
            </div>
            {currentPlyData && (
              <div className="analysis-annotation-badge" style={{ color: currentPlyData.annotation_color }}>
                {currentPlyData.annotation_symbol
                  ? `${currentPlyData.annotation_symbol} ${currentPlyData.annotation}`
                  : currentPlyData.annotation}
                {currentPlyData.is_player_move && currentPlyData.best_move_san && played_uci !== best_uci && (
                  <div className="analysis-best-hint">
                    Best: <strong>{currentPlyData.best_move_san}</strong>
                  </div>
                )}
              </div>
            )}
            {currentPly > 0 && currentPlyData?.explanation_text && (
              <div className="analysis-explanation-box">
                {currentPlyData.explanation_text}
              </div>
            )}
          </aside>

          {/* Center: Board + Controls */}
          <div className="analysis-center">
            <div className="analysis-board-wrap">
              <Chessboard
                board={board}
                lastMove={lastMove}
                possibleMoves={[]}
                inCheckCoord={null}
                premove={null}
                playerColor={playerColor}
                onSquareClick={() => {}}
                onRightClick={() => {}}
              />
              {/* Best-move arrow SVG overlay */}
              {bestArrow && (() => {
                const flip = (c: number) => playerColor === 'black' ? 7 - c : c;
                return (
                  <svg
                    className="best-move-arrow-svg"
                    viewBox="0 0 8 8"
                    preserveAspectRatio="none"
                  >
                    <defs>
                      <marker id="arrowhead" markerWidth="3" markerHeight="3" refX="1.5" refY="1.5" orient="auto">
                        <polygon points="0 0, 3 1.5, 0 3" fill="#f0c040" />
                      </marker>
                    </defs>
                    <line
                      x1={flip(bestArrow[1]) + 0.5}
                      y1={flip(bestArrow[0]) + 0.5}
                      x2={flip(bestArrow[3]) + 0.5}
                      y2={flip(bestArrow[2]) + 0.5}
                      stroke="#f0c040"
                      strokeWidth="0.15"
                      strokeLinecap="round"
                      strokeOpacity="0.85"
                      markerEnd="url(#arrowhead)"
                    />
                  </svg>
                );
              })()}
            </div>

            {/* Navigation controls */}
            <div className="analysis-controls">
              <button className="ctrl-btn" onClick={() => goTo(0)} title="Start (Home)">⏮</button>
              <button className="ctrl-btn" onClick={() => goTo(currentPly - 1)} title="Previous (←)" disabled={currentPly === 0}>◀</button>
              <span className="ctrl-ply">
                {currentPly === 0 ? 'Start' : `Move ${Math.ceil(currentPly / 2)} (${currentPly % 2 !== 0 ? 'White' : 'Black'})`}
              </span>
              <button className="ctrl-btn" onClick={() => goTo(currentPly + 1)} title="Next (→)" disabled={currentPly === totalPlies}>▶</button>
              <button className="ctrl-btn" onClick={() => goTo(totalPlies)} title="End (End)">⏭</button>
            </div>
          </div>

          {/* Right: Annotated Move List */}
          <aside className="analysis-right">
            <div className="analysis-panel-title">Moves</div>
            {/* Legend */}
            <div className="annotation-legend">
              {[['!!', '#f0c040', 'Brilliant'], ['!', '#54c481', 'Good'],
                ['?!', '#e6bc97', 'Inaccuracy'], ['?', '#e07030', 'Mistake'],
                ['??', '#b43232', 'Blunder']].map(([sym, col, label]) => (
                <span key={sym as string} style={{ color: col as string }} className="legend-item">
                  {sym} <span style={{ color: '#888', fontSize: '10px' }}>{label}</span>
                </span>
              ))}
            </div>
            <AnnotatedMoveList analysis={analysis} currentPly={currentPly} onPlyClick={goTo} />
          </aside>

        </div>
      )}
    </div>
  )
}
