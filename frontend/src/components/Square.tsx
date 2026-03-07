import Piece from './Piece'

type Props = {
  piece: string
  isLight: boolean
  coord: string
}

export default function Square({ piece, isLight, coord }: Props) {
  // We only show rank label on the 'a' file (coord ends in 'a')
  // We only show file label on the '1' rank (coord starts with '1')
  const showRank = coord.endsWith('a')
  const showFile = coord.startsWith('1')

  return (
    <div className={`square ${isLight ? 'light' : 'dark'}`}>
      {showRank && <span className="coord-rank">{coord[0]}</span>}
      {showFile && <span className="coord-file">{coord[1]}</span>}
      {piece ? <Piece code={piece} /> : null}
    </div>
  )
}
