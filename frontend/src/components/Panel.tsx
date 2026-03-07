import { useRef, useEffect } from 'react'

type Props = {
  moveHistory?: string[]
  turn?: 'white' | 'black'
  onResign?: () => void
}

export default function Panel({
  moveHistory = [],
  turn = 'white',
  onResign,
}: Props) {

  const logRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on every new move
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [moveHistory.length])

  return (
    <aside className="side-panel">
      <div className="panel-main">
        {/* Move History Header */}
        <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 className="panel-header-title">Move History</h3>

          {/* Turn Badge */}
          <div className="turn-badge">
            <div className={`turn-indicator-dot ${turn}`} />
            {turn === 'white' ? "White's Turn" : "Black's Turn"}
          </div>
        </div>

        {/* Move Log */}
        <div className="moves-log" ref={logRef}>
          {moveHistory.length === 0 ? (
            <div style={{ padding: '1rem', color: 'var(--text-muted)', textAlign: 'center', fontSize: '0.9rem' }}>
              Moves will appear here
            </div>
          ) : (
            moveHistory.reduce((result, move, index) => {
              if (index % 2 === 0) {
                result.push([move])
              } else {
                result[result.length - 1].push(move)
              }
              return result
            }, [] as string[][]).map((pair, idx) => (
              <div key={idx} className="move-row">
                <span className="move-number">{idx + 1}.</span>
                <span className="move-san">{pair[0]}</span>
                {pair[1] && <span className="move-san">{pair[1]}</span>}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="panel-footer">
          <button className="resign-btn" onClick={onResign}>Resign</button>
        </div>
      </div>
    </aside>
  )
}
