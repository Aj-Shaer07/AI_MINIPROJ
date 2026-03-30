import { useMemo, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import Chessboard from '../components/Chessboard'
import Panel from '../components/Panel'
import EvaluationBar from '../components/EvaluationBar'
import ExplainPopup from '../components/ExplainPopup'
import useGameController from '../hooks/useGameController'
import { DEFAULT_SETTINGS, DEFAULT_EVAL_INFO, type EvalInfo } from '../values'
import '../styles/chess.css'

export default function Game() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const settings = useMemo(() => {
    const isArena = searchParams.has('arena')
    return {
      timeControl: searchParams.get('time') || DEFAULT_SETTINGS.timeControl,
      increment: searchParams.get('inc') || DEFAULT_SETTINGS.increment,
      playerColor: (searchParams.get('color') as 'white' | 'black') || DEFAULT_SETTINGS.playerColor,
      showPlayerClock: searchParams.has('pclock') ? searchParams.get('pclock') === 'true' : DEFAULT_SETTINGS.showPlayerClock,
      showEngineClock: searchParams.has('eclock') ? searchParams.get('eclock') === 'true' : DEFAULT_SETTINGS.showEngineClock,
      enableCoachMode: searchParams.has('coach') ? searchParams.get('coach') === 'true' : DEFAULT_SETTINGS.enableCoachMode,
      botId: searchParams.get('bot') || undefined,
      isArena,
      arenaDepth: isArena ? parseInt(searchParams.get('depth') || '4') : 4,
      arenaQuality: isArena ? parseInt(searchParams.get('quality_tier') || '0') : 0,
    }
  }, [searchParams])

  const gc = useGameController({
    playerColor: settings.playerColor,
    timeControlMin: parseInt(settings.timeControl) || 5,
    incrementSec: parseInt(settings.increment) || 0,
    enableCoachMode: settings.enableCoachMode,
    enableClocks: settings.showPlayerClock || settings.showEngineClock,
    botId: settings.botId,
    // Inject arena params so useGameController can use them for search
    isArena: settings.isArena,
    arenaDepth: settings.arenaDepth,
    arenaQuality: settings.arenaQuality,
  })
  const [selected, setSelected] = useState<[number, number] | null>(null)

  const handleSquareClick = async (r: number, c: number) => {
    if (gc.gameOverReason) return
    const piece = gc.board[r][c]
    const isPlayerPiece = piece && (
      (settings.playerColor === 'white' && piece === piece.toUpperCase()) ||
      (settings.playerColor === 'black' && piece !== piece.toUpperCase())
    )

    // Select own piece (even out-of-turn to queue premove)
    if (isPlayerPiece) {
      setSelected([r, c])
      gc.setPossibleMoves(await gc.getLegalMoves(r, c).catch(() => []))
      return
    }

    // Attempt move / premove
    if (selected) {
      const [fr, fc] = selected
      const isPossible = gc.possibleMoves.some(([rr, cc]) => rr === r && cc === c)
      setSelected(null)
      gc.setPossibleMoves([])
      if (isPossible) await gc.movePiece(fr, fc, r, c)
    }
  }

  const formatTime = (ms: number) => {
    const total = Math.max(0, Math.floor(ms / 1000))
    const m = Math.floor(total / 60).toString().padStart(2, '0')
    const s = (total % 60).toString().padStart(2, '0')
    return total < 20 ? `${m}:${s}.${Math.floor((Math.max(0, ms) % 1000) / 100)}` : `${m}:${s}`
  }

  const playerTimeMs = settings.playerColor === 'white' ? gc.whiteTime : gc.blackTime
  const engineTimeMs = settings.playerColor === 'white' ? gc.blackTime : gc.whiteTime

  const evalInfo: EvalInfo | null = gc.evalCp !== 0 || gc.evalInfo ? {
    ...DEFAULT_EVAL_INFO,
    ...(gc.evalInfo || {}),
    eval_cp: gc.evalCp,
  } : null

  // ─── Game-over overlay config ─────────────────────────────────────────────
  const gameOverTitle = () => {
    if (!gc.gameOverReason) return ''
    if (gc.gameOverReason === 'checkmate') {
      // whoever just moved won — turn is now the loser's turn
      const winner = gc.turn === 'white' ? 'Black' : 'White'
      return `${winner} wins by Checkmate`
    }
    if (gc.gameOverReason === 'stalemate') return 'Draw by Stalemate'
    if (gc.gameOverReason === 'time') {
      const loser = gc.turn
      const winner = loser === 'white' ? 'Black' : 'White'
      return `${winner} wins on Time`
    }
    if (gc.gameOverReason === 'resign') return 'You Resigned'
    return 'Game Over'
  }

  const engineColor = settings.playerColor === 'white' ? 'black' : 'white'

  return (
    <div className="game-page">
      {/* Game-over overlay */}
      {gc.gameOverReason && (
        <div className="game-over-overlay">
          <div className="game-over-card">
            <div className="game-over-icon">
              {gc.gameOverReason === 'checkmate' ? '♔' : gc.gameOverReason === 'stalemate' ? '½' : gc.gameOverReason === 'resign' ? '🏳' : '⏱'}
            </div>
            <h2 className="game-over-title">{gameOverTitle()}</h2>
            <p className="game-over-moves">
              {gc.moveHistory.length} move{gc.moveHistory.length !== 1 ? 's' : ''} played
            </p>
            <div className="game-over-actions">
              {settings.isArena ? (
                <button
                  className="btn btn-primary btn-large"
                  onClick={async () => {
                    // Report result back to Arena then redirect
                    import('../utils/api').then(api => {
                      let result: 'win' | 'loss' | 'draw' = 'draw'
                      if (gc.gameOverReason === 'checkmate' || gc.gameOverReason === 'resign' || gc.gameOverReason === 'time') {
                        // If turn != playerColor, it means player just moved and won
                        const playerWon = gc.turn !== settings.playerColor
                        result = playerWon ? 'win' : 'loss'
                      }
                      api.arenaReportResult(result).then(res => {
                        navigate(`/arena?result=${result}&msg=${encodeURIComponent(res.message)}`)
                      }).catch(() => navigate('/arena'))
                    })
                  }}
                >
                  Return to Arena →
                </button>
              ) : (
                <>
                  <button className="restart-btn" onClick={() => navigate('/')}>New Game</button>
                  {gc.moveHistory.length > 0 && (
                    <button
                      className="analysis-btn"
                      onClick={() => navigate(`/analysis?color=${settings.playerColor}`, {
                        state: { history: gc.moveHistory, playerColor: settings.playerColor }
                      })}
                    >
                      Post-Game Analysis
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="game-layout">
        <EvaluationBar evalCp={gc.evalCp} playerColor={settings.playerColor} />

        <div className="board-column">
          {/* Top Player (Engine) */}
          <div className="player-bar top-player">
            <div className="player-info">
              <div className={`avatar ${engineColor}`}>{engineColor === 'white' ? 'W' : 'B'}</div>
              <span className="player-name">Engine</span>
            </div>
            {settings.showEngineClock && (
              <div className={`player-clock ${gc.turn !== settings.playerColor && !gc.gameOverReason ? 'active-clock' : ''}`}>
                <span className="time">{formatTime(engineTimeMs)}</span>
              </div>
            )}
          </div>

          <div className="board-wrap">
            <Chessboard
              board={gc.board}
              lastMove={gc.lastMove}
              possibleMoves={gc.possibleMoves}
              inCheckCoord={gc.inCheckCoord}
              premove={gc.premove}
              playerColor={settings.playerColor}
              onSquareClick={handleSquareClick}
              onRightClick={gc.clearPremove}
            />
          </div>

          {/* Bottom Player (You) */}
          <div className="player-bar bottom-player">
            <div className="player-info">
              <div className={`avatar ${settings.playerColor}`}>{settings.playerColor === 'white' ? 'W' : 'B'}</div>
              <span className="player-name">You</span>
            </div>
            {settings.showPlayerClock && (
              <div className={`player-clock ${gc.turn === settings.playerColor && !gc.gameOverReason ? 'active-clock' : ''}`}>
                <span className="time">{formatTime(playerTimeMs)}</span>
              </div>
            )}
          </div>
        </div>

        <Panel
          moveHistory={gc.moveHistory}
          turn={gc.turn}
          onResign={gc.resign}
        />

        {/* Engine Evaluation side column */}
        {evalInfo && (
          <aside className="engine-eval-box">
            <div className="eval-box-header">Engine Evaluation</div>
            <div className="eval-grid">
              {[
                ['Eval (cp)', evalInfo.eval_cp],
                ['Depth', evalInfo.depth],
                ['Time (s)', evalInfo.time_s],
                ['Nodes', evalInfo.nodes],
                ['Q-Nodes', evalInfo.q_nodes],
                ['Cutoffs', evalInfo.cutoffs],
                ['TT Hits', evalInfo.tt_hits],
                ['TT Probes', evalInfo.tt_probes],
                ['Max Ply', evalInfo.max_ply],
                ['Max Q-Ply', evalInfo.max_q_ply],
              ].map(([label, val]) => (
                <div key={label as string} className="eval-grid-row">
                  <span className="eval-label">{label}</span>
                  <span className="eval-val">{val ?? 0}</span>
                </div>
              ))}
              {evalInfo.mate_in !== undefined && (
                <div className="eval-grid-row">
                  <span className="eval-label" style={{ color: 'var(--accent-gold)' }}>Mate In</span>
                  <span className="eval-val">{evalInfo.mate_in}</span>
                </div>
              )}
            </div>
          </aside>
        )}
        <ExplainPopup explanationData={gc.explanationData} />
      </div>
    </div>
  )
}
