import Square from './Square.tsx'
import '../styles/chess.css'

type Props = {
  board?: string[][]
  onSquareClick?: (r:number,c:number)=>void
  lastMove?: [number,number,number,number] | null
  possibleMoves?: Array<[number,number]>
}

export default function Chessboard({ board, onSquareClick, lastMove = null, possibleMoves = [] }: Props) {
  const initialBoard: string[][] = board ?? [
    ['r','n','b','q','k','b','n','r'],
    ['p','p','p','p','p','p','p','p'],
    ['','','','','','','',''],
    ['','','','','','','',''],
    ['','','','','','','',''],
    ['','','','','','','',''],
    ['P','P','P','P','P','P','P','P'],
    ['R','N','B','Q','K','B','N','R'],
  ]

  const isInMoves = (r:number,c:number) => possibleMoves.some(([rr,cc])=>rr===r&&cc===c)

  return (
    <div className="chessboard" role="grid" aria-label="Chessboard">
      {initialBoard.map((row, rIdx) => (
        <div key={rIdx} className="board-row" role="row">
          {row.map((piece, fIdx) => {
            const isLight = (rIdx + fIdx) % 2 === 0
            const coord = `${8 - rIdx}${String.fromCharCode(97 + fIdx)}`
            const isLast = lastMove ? (lastMove[0]===rIdx&&lastMove[1]===fIdx)||(lastMove[2]===rIdx&&lastMove[3]===fIdx) : false
            return (
              <div key={fIdx} className={`square-wrap ${isLast? 'last-move':''} ${isInMoves(rIdx,fIdx)?'possible':''}`} onClick={() => onSquareClick?.(rIdx,fIdx)}>
                <Square
                  piece={piece}
                  isLight={isLight}
                  coord={coord}
                />
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}
