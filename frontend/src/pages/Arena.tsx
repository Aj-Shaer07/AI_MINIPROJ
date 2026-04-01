import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { arenaGetSession, arenaResetSession, type ArenaSession } from '../utils/api'
import { TIME_OPTIONS, INCREMENT_OPTIONS, COLOR_OPTIONS, DEFAULT_SETTINGS } from '../values'

// ── ELO Ladder table (mirrors backend) ──────────────────
const QUALITY_LABELS = ['4th Best', '3rd Best', '2nd Best', 'Best Move']
const LADDER: Record<string, number> = {
  '3-0': 600,  '3-1': 750,  '3-2': 900,  '3-3': 1050,
  '4-0': 1050, '4-1': 1200, '4-2': 1350, '4-3': 1500,
  '5-0': 1500, '5-1': 1650, '5-2': 1800, '5-3': 1950,
  '6-0': 1950, '6-1': 2050, '6-2': 2150, '6-3': 2250,
  '7-0': 2250, '7-1': 2350, '7-2': 2450, '7-3': 2500,
}

function getElo(depth: number, quality: number) {
  return LADDER[`${depth}-${quality}`] ?? 1050
}

export default function Arena() {
  const navigate = useNavigate()
  const [session, setSession] = useState<ArenaSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [resetting, setResetting] = useState(false)
  const [resultMsg, setResultMsg] = useState<string | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)

  // ── Game settings (mirrors Landing.tsx) ──────────────────
  const [timeControl, setTimeControl] = useState(DEFAULT_SETTINGS.timeControl)
  const [increment, setIncrement] = useState(DEFAULT_SETTINGS.increment)
  const [playerColor, setPlayerColor] = useState<'white' | 'black'>(DEFAULT_SETTINGS.playerColor)
  const [showPlayerClock, setShowPlayerClock] = useState(DEFAULT_SETTINGS.showPlayerClock)
  const [showEngineClock, setShowEngineClock] = useState(DEFAULT_SETTINGS.showEngineClock)
  const [enableCoachMode, setEnableCoachMode] = useState(DEFAULT_SETTINGS.enableCoachMode)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const msgParam = params.get('msg')
    if (msgParam) setResultMsg(decodeURIComponent(msgParam))

    arenaGetSession()
      .then(s => { setSession(s); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const handleStartGame = async () => {
    if (!session) return
    navigate(
      `/game?time=${timeControl}&inc=${increment}&color=${playerColor}` +
      `&pclock=${showPlayerClock}&eclock=${showEngineClock}&coach=${enableCoachMode}` +
      `&arena=true&depth=${session.depth}&quality_tier=${session.quality_tier}`
    )
  }

  const handleReset = async () => {
    setResetting(true)
    try {
      const res = await arenaResetSession()
      setSession(res.session)
      setResultMsg(null)
    } finally {
      setResetting(false)
    }
  }

  if (loading) {
    return (
      <div className="arena-page">
        <div className="arena-loading">Loading Arena...</div>
      </div>
    )
  }

  const elo = session ? getElo(session.depth, session.quality_tier) : 1050
  const totalGames = session ? session.games_played : 0
  const winRate = totalGames > 0 && session
    ? Math.round((session.wins / totalGames) * 100)
    : 0

  const qualityLabel = session ? QUALITY_LABELS[session.quality_tier] ?? 'Best' : '4th Best'

  return (
    <div className="arena-page">
      {/* ── Header ─────────────────────────────────────────── */}
      <div className="arena-header">
        <div className="arena-title-row">
          <h1 className="arena-title">Self-Paced Arena</h1>
        </div>
        <p className="arena-subtitle">
          {session?.calibrated
            ? 'Your ELO is being tracked. Keep playing to refine it.'
            : 'Calibration match in progress. Play your first game to set your baseline.'}
        </p>
      </div>

      {/* ── ELO badge ────────────────────────────────────────── */}
      <div className="arena-elo-card">
        <div className="elo-badge-large">
          <span className="elo-number">{elo}</span>
          <span className="elo-label">Estimated ELO</span>
        </div>
        <div className="arena-difficulty">
          <div className="difficulty-stat">
            <span className="diff-label">Engine Depth</span>
            <span className="diff-value">{session?.depth ?? 4}</span>
          </div>
          <div className="difficulty-divider" />
          <div className="difficulty-stat">
            <span className="diff-label">Move Quality</span>
            <span className="diff-value">{qualityLabel}</span>
          </div>
          <div className="difficulty-divider" />
          {session?.calibrated ? (
            <div className="difficulty-stat">
              <span className="diff-label">Status</span>
              <span className="diff-value diff-calibrated">✓ Calibrated</span>
            </div>
          ) : (
            <div className="difficulty-stat">
              <span className="diff-label">Status</span>
              <span className="diff-value diff-uncalibrated">⟳ Calibrating</span>
            </div>
          )}
        </div>
      </div>

      {/* ── Result message ────────────────────────────────────── */}
      {resultMsg && (
        <div className="arena-result-msg">
          {resultMsg}
        </div>
      )}

      {/* ── Record ───────────────────────────────────────────── */}
      {totalGames > 0 && session && (
        <div className="arena-record-row">
          <div className="record-stat wins">
            <span className="record-num">{session.wins}</span>
            <span className="record-lbl">Wins</span>
          </div>
          <div className="record-stat draws">
            <span className="record-num">{session.draws}</span>
            <span className="record-lbl">Draws</span>
          </div>
          <div className="record-stat losses">
            <span className="record-num">{session.losses}</span>
            <span className="record-lbl">Losses</span>
          </div>
          <div className="record-stat rate">
            <span className="record-num">{winRate}%</span>
            <span className="record-lbl">Win Rate</span>
          </div>
        </div>
      )}

      {/* ── ELO Ladder progress ───────────────────────────────── */}
      <div className="arena-ladder">
        <h3 className="ladder-title">ELO Ladder</h3>
        <div className="ladder-grid">
          {[3, 4, 5, 6, 7].map(d => (
            <div key={d} className="ladder-row">
              <span className="ladder-depth">Depth {d}</span>
              {[0, 1, 2, 3].map(q => {
                const cellElo = getElo(d, q)
                const isCurrent = session?.depth === d && session?.quality_tier === q
                const isBelow = cellElo < elo
                return (
                  <div
                    key={q}
                    className={`ladder-cell ${isCurrent ? 'current' : ''} ${isBelow && !isCurrent ? 'achieved' : ''}`}
                    title={`${QUALITY_LABELS[q]} — ~${cellElo} ELO`}
                  >
                    <span className="cell-elo">{cellElo}</span>
                    <span className="cell-q">{QUALITY_LABELS[q].split(' ')[0]}</span>
                    {isCurrent && <span className="cell-arrow">▶</span>}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>

      {/* ── Game Settings (collapsible) ───────────────────────── */}
      <div className="arena-settings-section">
        <button
          className="arena-settings-toggle"
          onClick={() => setSettingsOpen(o => !o)}
          aria-expanded={settingsOpen}
        >
          <span>⚙ Game Settings</span>
          <span className="settings-toggle-hint">
            {playerColor === 'white' ? '♔ White' : '♚ Black'} · {timeControl}m+{increment}s
            {enableCoachMode ? ' · Coach ON' : ''}
          </span>
          <span className="settings-chevron">{settingsOpen ? '▲' : '▼'}</span>
        </button>

        {settingsOpen && (
          <div className="arena-settings-panel">
            {/* Play As */}
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

            {/* Time Control */}
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

            {/* Increment */}
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

            {/* Options */}
            <div className="settings-section">
              <label className="settings-label">Options</label>
              <div className="checkbox-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={showPlayerClock}
                    onChange={e => setShowPlayerClock(e.target.checked)}
                  />
                  <span className="checkbox-custom" />
                  Player Clock
                </label>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={showEngineClock}
                    onChange={e => setShowEngineClock(e.target.checked)}
                  />
                  <span className="checkbox-custom" />
                  Engine Clock
                </label>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={enableCoachMode}
                    onChange={e => setEnableCoachMode(e.target.checked)}
                  />
                  <span className="checkbox-custom" />
                  Coach Mode (Explainable AI)
                </label>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Actions ──────────────────────────────────────────── */}
      <div className="arena-actions">
        <button className="btn btn-primary btn-large" onClick={handleStartGame}>
          {totalGames === 0 ? 'Start Calibration Game' : '▶ Next Arena Game'}
        </button>
        <button
          className="btn btn-outline"
          onClick={handleReset}
          disabled={resetting}
        >
          {resetting ? 'Resetting...' : '↺ Reset Session'}
        </button>
        <button className="btn btn-ghost" onClick={() => navigate('/')}>
          ← Back to Lobby
        </button>
      </div>
    </div>
  )
}
