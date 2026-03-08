import { useNavigate, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { TIME_OPTIONS, INCREMENT_OPTIONS, COLOR_OPTIONS, DEFAULT_SETTINGS } from '../values'
import { getBots, type Bot } from '../utils/api'
import '../styles/chess.css'

// Step 0 = hero, Step 1 = game settings, Step 2 = bot selection
type Step = 0 | 1 | 2

// Bot level metadata used only for presentation (avatars, descriptions, etc.)
const BOT_META: Record<string, { emoji: string; desc: string; rating: string; depth: number }> = {
  bot1: { emoji: '🐣', desc: 'Makes random-ish moves. Perfect for beginners.', rating: '~800', depth: 3 },
  bot2: { emoji: '🙂', desc: 'Plays basic tactics. A good casual opponent.', rating: '~1200', depth: 5 },
  bot3: { emoji: '🧐', desc: 'Understands strategy and plans ahead.', rating: '~1500', depth: 4 },
  bot4: { emoji: '🔥', desc: 'Aggressive and hard to beat. Plays deep combinations.', rating: '~2000', depth: 7 },
  bot5: { emoji: '🤖', desc: 'Near-perfect play. Only for the brave.', rating: '~2300', depth: 6 },
}

export default function Landing() {
  const navigate = useNavigate()
  const location = useLocation()
  const [step, setStep] = useState<Step>(0)
  const [timeControl, setTimeControl] = useState(DEFAULT_SETTINGS.timeControl)
  const [increment, setIncrement] = useState(DEFAULT_SETTINGS.increment)
  const [playerColor, setPlayerColor] = useState(DEFAULT_SETTINGS.playerColor)
  const [showPlayerClock, setShowPlayerClock] = useState(DEFAULT_SETTINGS.showPlayerClock)
  const [showEngineClock, setShowEngineClock] = useState(DEFAULT_SETTINGS.showEngineClock)
  const [enableCoachMode, setEnableCoachMode] = useState(DEFAULT_SETTINGS.enableCoachMode)
  const [bots, setBots] = useState<Bot[]>([])
  const [hoveredBot, setHoveredBot] = useState<string | null>(null)

  // Reset step if brand link clicked (detected via state)
  useEffect(() => {
    if ((location.state as any)?.reset) {
      setStep(0)
      // Clear state so it doesn't reset again on other navigation
      window.history.replaceState({}, document.title)
    }
  }, [location])

  // Tiny preview board
  const previewBoard = [
    ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
    ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
    ['', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', ''],
    ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
    ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R'],
  ]
  const SYMBOLS: Record<string, string> = {
    K: '♔', Q: '♕', R: '♖', B: '♗', N: '♘', P: '♙',
    k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟',
  }

  // Fetch bots when entering step 2
  useEffect(() => {
    if (step === 2) {
      getBots()
        .then(r => setBots(r.bots))
        .catch(() => setBots([
          { id: 'bot1', name: 'Beginner Bot', elo: 'Elo 800' },
          { id: 'bot2', name: 'Casual Bot', elo: 'Elo 1200' },
          { id: 'bot3', name: 'Intermediate Bot', elo: 'Elo 1500' },
          { id: 'bot4', name: 'Advanced Bot', elo: 'Elo 2000' },
          { id: 'bot5', name: 'Expert Bot', elo: 'Elo 2500' },
        ]))
    }
  }, [step])

  const handleSelectBot = (botId: string) => {
    navigate(`/game?time=${timeControl}&inc=${increment}&color=${playerColor}&pclock=${showPlayerClock}&eclock=${showEngineClock}&coach=${enableCoachMode}&bot=${botId}`)
  }

  // ─── Hero Screen ──────────────────────────────────────────────────────────
  if (step === 0) {
    return (
      <div className="landing">
        <div className="landing-hero">
          <div className="landing-content">
            <h1>Play Chess Online</h1>
            <p className="landing-subtitle">
              Challenge our AI engine and sharpen your skills. <br />
              Beautiful interface, smart opponent, real-time analysis.
            </p>
            <div className="landing-actions">
              <button className="btn btn-primary btn-large" onClick={() => setStep(1)}>
                Start Game
              </button>
            </div>
          </div>
          <div className="landing-board-preview">
            <div className="preview-board">
              {previewBoard.map((row, r) => (
                <div key={r} className="preview-row">
                  {row.map((piece, c) => (
                    <div key={c} className={`preview-square ${(r + c) % 2 === 0 ? 'light' : 'dark'}`}>
                      {piece && (
                        <span className={`preview-piece ${piece === piece.toUpperCase() ? 'white' : 'black'}`}>
                          {SYMBOLS[piece]}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ─── Game Settings Screen ─────────────────────────────────────────────────
  if (step === 1) {
    return (
      <div className="landing">
        <div className="settings-card">
          {/* Step indicator */}
          <div className="step-indicator">
            <div className="step-dot active" />
            <div className="step-line" />
            <div className="step-dot" />
          </div>

          <h2 className="settings-title">Game Settings</h2>

          <div className="settings-section">
            <label className="settings-label">Time Control</label>
            <div className="button-group">
              {TIME_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  className={`group-btn ${timeControl === opt.value ? 'active' : ''}`}
                  onClick={() => setTimeControl(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="settings-section">
            <label className="settings-label">Increment (per move)</label>
            <div className="button-group">
              {INCREMENT_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  className={`group-btn ${increment === opt.value ? 'active' : ''}`}
                  onClick={() => setIncrement(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="settings-section">
            <label className="settings-label">Play As</label>
            <div className="button-group">
              {COLOR_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  className={`group-btn ${playerColor === opt.value ? 'active' : ''}`}
                  onClick={() => setPlayerColor(opt.value as 'white' | 'black')}
                >
                  <div className={`color-dot ${opt.value}`} />
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="settings-section">
            <label className="settings-label">Clock Visibility</label>
            <div className="checkbox-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={showPlayerClock}
                  onChange={(e) => setShowPlayerClock(e.target.checked)}
                />
                <span className="checkbox-custom"></span>
                Player Clock
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={showEngineClock}
                  onChange={(e) => setShowEngineClock(e.target.checked)}
                />
                <span className="checkbox-custom"></span>
                Engine Clock
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={enableCoachMode}
                  onChange={(e) => setEnableCoachMode(e.target.checked)}
                />
                <span className="checkbox-custom"></span>
                Coach Mode (Explainable AI)
              </label>
            </div>
          </div>

          <div className="settings-summary">
            Time: {timeControl}m | Inc: {increment}s | P-Clock: {showPlayerClock ? 'ON' : 'OFF'} | E-Clock: {showEngineClock ? 'ON' : 'OFF'} | Color: {playerColor}
          </div>

          <div className="settings-footer">
            <button className="btn btn-outline" onClick={() => setStep(0)}>Back</button>
            <button className="btn btn-primary" onClick={() => setStep(2)}>
              Choose Opponent →
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ─── Bot Selection Screen ─────────────────────────────────────────────────
  return (
    <div className="landing">
      <div className="bot-selection-card">
        {/* Step indicator */}
        <div className="step-indicator">
          <div className="step-dot done" />
          <div className="step-line done" />
          <div className="step-dot active" />
        </div>

        <h2 className="settings-title">Choose Your Opponent</h2>
        <p className="bot-selection-subtitle">Select a bot to play against. Each plays at a different skill level.</p>

        <div className="bot-grid">
          {bots.map((bot) => {
            const meta = BOT_META[bot.id] ?? { emoji: '🤖', desc: '', rating: '', depth: 3 }
            const isHovered = hoveredBot === bot.id
            return (
              <button
                key={bot.id}
                className={`bot-card ${isHovered ? 'bot-card-hovered' : ''}`}
                onMouseEnter={() => setHoveredBot(bot.id)}
                onMouseLeave={() => setHoveredBot(null)}
                onClick={() => handleSelectBot(bot.id)}
              >
                <div className="bot-avatar">{meta.emoji}</div>
                <div className="bot-info">
                  <span className="bot-name">{bot.name}</span>
                  <span className="bot-elo">{bot.elo}</span>
                  <span className="bot-depth">Depth {meta.depth}</span>
                  <span className="bot-desc">{meta.desc}</span>
                </div>
                <div className="bot-play-arrow">▶</div>
              </button>
            )
          })}
        </div>

        <div className="settings-footer" style={{ justifyContent: 'flex-start' }}>
          <button className="btn btn-outline" onClick={() => setStep(1)}>← Back to Settings</button>
        </div>
      </div>
    </div>
  )
}
