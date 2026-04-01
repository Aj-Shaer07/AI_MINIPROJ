import Piece from './Piece'

type Props = {
  piece: string
  isLight: boolean
  coord: string
  isBottomEdge?: boolean
  isLeftEdge?: boolean
}

export default function Square({ piece, isLight, coord, isBottomEdge, isLeftEdge }: Props) {
  // We show rank label (number) on the left edge.
  // We show file label (letter) on the bottom edge.
  // If edges are not provided (e.g., preview boards), fallback to standard 'a' file and '1' rank.
  const showRank = isLeftEdge ?? coord.endsWith('a')
  const showFile = isBottomEdge ?? coord.startsWith('1')

  return (
    <div className={`square ${isLight ? 'light' : 'dark'}`}>
      {showRank && <span className="coord-rank">{coord[1]}</span>}
      {showFile && <span className="coord-file">{coord[0]}</span>}
      {piece ? <Piece code={piece} /> : null}
    </div>
  )
}
