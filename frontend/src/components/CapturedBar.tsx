type Props = { captured: string[]; label?: string }

const SYMBOLS: Record<string, string> = {
  K: '♔', Q: '♕', R: '♖', B: '♗', N: '♘', P: '♙',
  k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟',
}

export default function CapturedBar({ captured, label = '' }: Props) {
  return (
    <div className="captured-bar">
      {label ? <div className="captured-label">{label}</div> : null}
      <div className="captured-items">
        {captured.map((c, i) => (
          <span key={i} className="captured-piece">{SYMBOLS[c] ?? c}</span>
        ))}
      </div>
    </div>
  )
}
