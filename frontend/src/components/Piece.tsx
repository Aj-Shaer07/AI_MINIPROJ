type Props = { code: string }

const SYMBOLS: Record<string, string> = {
  K: '♔', Q: '♕', R: '♖', B: '♗', N: '♘', P: '♙',
  k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟',
}

export default function Piece({ code }: Props) {
  const symbol = SYMBOLS[code] ?? ''
  const colorClass = code === code.toUpperCase() ? 'white' : 'black'
  return <span className={`piece ${colorClass}`}>{symbol}</span>
}
