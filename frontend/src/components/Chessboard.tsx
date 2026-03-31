import Square from './Square'
import '../styles/chess.css'

type Props = {
  board?: string[][]
  onSquareClick?: (r: number, c: number) => void
  lastMove?: [number, number, number, number] | null
  possibleMoves?: Array<[number, number]>
  inCheckCoord?: [number, number] | null
  premove?: { from: string, to: string } | null
  playerColor?: 'white' | 'black'
  onRightClick?: () => void
}

export default function Chessboard({
  board,
  onSquareClick,
  lastMove = null,
  possibleMoves = [],
  inCheckCoord = null,
  premove = null,
  playerColor = 'white',
  onRightClick,
}: Props) {
  const initialBoard: string[][] = board ?? [
    ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
    ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
    ['', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', ''],
    ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
    ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R'],
  ]

  const isInMoves = (r: number, c: number) =>
    possibleMoves.some(([rr, cc]) => rr === r && cc === c)

  let renderedBoard = initialBoard
  if (playerColor === 'black') {
    renderedBoard = [...initialBoard].reverse().map(row => [...row].reverse())
  }

  const arrows: { x1: number, y1: number, x2: number, y2: number, color: string, id: string }[] = []

  const addArrow = (r1: number, c1: number, r2: number, c2: number, color: string, id: string) => {
    const fromRIdx = playerColor === 'black' ? 7 - r1 : r1
    const fromCIdx = playerColor === 'black' ? 7 - c1 : c1
    const toRIdx = playerColor === 'black' ? 7 - r2 : r2
    const toCIdx = playerColor === 'black' ? 7 - c2 : c2

    const x1 = fromCIdx + 0.5
    const y1 = fromRIdx + 0.5
    const x2 = toCIdx + 0.5
    const y2 = toRIdx + 0.5

    const dx = x2 - x1
    const dy = y2 - y1
    const dist = Math.sqrt(dx * dx + dy * dy)

    let endX = x2
    let endY = y2
    if (dist > 0) {
      const shortenBy = 0.35
      endX = x2 - (dx / dist) * shortenBy
      endY = y2 - (dy / dist) * shortenBy
    }

    arrows.push({ x1, y1, x2: endX, y2: endY, color, id })
  }

  if (lastMove) {
    addArrow(lastMove[0], lastMove[1], lastMove[2], lastMove[3], 'var(--arrow-last-move)', 'last-move-arrow')
  }

  if (premove) {
    const f1 = premove.from.charCodeAt(0) - 97
    const r1 = 8 - parseInt(premove.from[1], 10)
    const f2 = premove.to.charCodeAt(0) - 97
    const r2 = 8 - parseInt(premove.to[1], 10)
    addArrow(r1, f1, r2, f2, 'var(--arrow-premove)', 'premove-arrow')
  }

  const arrowOverlay = arrows.length > 0 ? (
    <svg
      viewBox="0 0 8 8"
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 10,
      }}
    >
      <defs>
        {arrows.map((arr) => (
          <marker
            key={`arrowhead-${arr.id}`}
            id={`arrowhead-${arr.id}`}
            markerWidth="3"
            markerHeight="3"
            refX="1.5"
            refY="1.5"
            orient="auto"
          >
            <polygon points="0 0, 3 1.5, 0 3" fill={arr.color} />
          </marker>
        ))}
      </defs>
      {arrows.map((arr) => (
        <line
          key={`line-${arr.id}`}
          x1={arr.x1}
          y1={arr.y1}
          x2={arr.x2}
          y2={arr.y2}
          stroke={arr.color}
          strokeWidth="0.15"
          strokeLinecap="round"
          markerEnd={`url(#arrowhead-${arr.id})`}
        />
      ))}
    </svg>
  ) : null

  return (
    <div className="chessboard" role="grid" aria-label="Chessboard">
      {renderedBoard.map((row, visualRIdx) => (
        <div key={visualRIdx} className="board-row" role="row">
          {row.map((piece, visualFIdx) => {
            const isLight = (visualRIdx + visualFIdx) % 2 === 0

            // map back to absolute standard logic indices
            const rIdx = playerColor === 'black' ? 7 - visualRIdx : visualRIdx
            const fIdx = playerColor === 'black' ? 7 - visualFIdx : visualFIdx

            // rank is 8-rIdx (8 to 1)
            // file is char 97+fIdx (a to h)
            const coord = `${String.fromCharCode(97 + fIdx)}${8 - rIdx}`

            const isLast = lastMove
              ? (lastMove[0] === rIdx && lastMove[1] === fIdx) ||
              (lastMove[2] === rIdx && lastMove[3] === fIdx)
              : false
            const isPossible = isInMoves(rIdx, fIdx)
            // If the square has a piece and is a possible move, it's a capture
            const captureClass = isPossible && piece !== '' ? 'has-piece' : ''
            const isCheck = inCheckCoord ? inCheckCoord[0] === rIdx && inCheckCoord[1] === fIdx : false
            const isPremove = premove ? premove.from === coord || premove.to === coord : false

            return (
              <div
                key={visualFIdx}
                className={`square-wrap ${isLast ? 'last-move' : ''} ${isPossible ? 'possible' : ''} ${captureClass} ${isCheck ? 'in-check' : ''} ${isPremove ? 'premove' : ''}`}
                onClick={() => onSquareClick?.(rIdx, fIdx)}
                onContextMenu={(e) => {
                  e.preventDefault()
                  onRightClick?.()
                }}
              >
                <Square
                  piece={piece}
                  isLight={isLight}
                  coord={coord}
                  isBottomEdge={visualRIdx === 7}
                  isLeftEdge={visualFIdx === 0}
                />
              </div>
            )
          })}
        </div>
      ))}
      {arrowOverlay}
    </div>
  )
}
