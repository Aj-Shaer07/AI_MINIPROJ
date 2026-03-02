import Piece from './Piece.tsx'

type Props = {
  piece: string
  isLight: boolean
  coord: string
}

export default function Square({ piece, isLight }: Props) {
  return (
    <div className={`square ${isLight ? 'light' : 'dark'}`}>
      {piece ? <Piece code={piece} /> : null}
    </div>
  )
}
