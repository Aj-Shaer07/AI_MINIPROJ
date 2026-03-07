import { PIECE_SYMBOLS } from '../values'

type Props = { captured: string[]; label?: string }

export default function CapturedBar({ captured, label = '' }: Props) {
  return (
    <div className="captured-bar">
      {label && <div className="captured-label" style={{ display: 'none' }}>{label}</div>}
      <div className="captured-items">
        {captured.map((c, i) => (
          <span key={i} className="captured-piece" style={c === c.toUpperCase() ? { color: '#fff8e6', textShadow: '0 1px 2px rgba(0,0,0,0.5), -1px -1px 0 #555, 1px -1px 0 #555, -1px 1px 0 #555, 1px 1px 0 #555' } : { color: '#111' }}>
            {PIECE_SYMBOLS[c] ?? c}
          </span>
        ))}
      </div>
    </div>
  )
}
