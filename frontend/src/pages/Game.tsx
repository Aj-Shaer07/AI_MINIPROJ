import Chessboard from '../components/Chessboard.tsx'
import Panel from '../components/Panel'
import EvaluationBar from '../components/EvaluationBar'
import useGameController from '../hooks/useGameController'
import '../styles/chess.css'

export default function Game() {
  const gc = useGameController()

  const handleSquareClick = (r:number,c:number) => {
    // naive click: if no selection, try to pick piece; otherwise move from selected
    // For now implement a single-click move: if selected square differs, move last selected to clicked if possible
    // Simple behavior: move a non-empty piece to clicked spot when source != dest
    const board = gc.board
    // find a piece that was clicked previously? we'll implement: if clicked square has a piece, mark possible moves (stub)
    const piece = board[r][c]
    if (piece) {
      // show naive possible moves (allow moving one step forward/back)
      gc.setPossibleMoves([[r+1, c], [r-1, c]].filter(([rr,cc])=>rr>=0&&rr<8&&cc>=0&&cc<8) as any)
      return
    }
    // otherwise if no piece, try to move from a selected candidate (use lastMove origin if present)
    if (gc.lastMove) {
      const [fr,fc] = [gc.lastMove[0], gc.lastMove[1]]
      gc.movePiece(fr, fc, r, c)
    }
  }

  return (
    <div className="game-page">
      <div className="game-grid">
        <EvaluationBar evalCp={gc.evalCp} />
        <div className="board-wrap">
          <Chessboard board={gc.board} lastMove={gc.lastMove} possibleMoves={gc.possibleMoves} onSquareClick={handleSquareClick} />
        </div>
        <Panel whiteCaptured={gc.whiteCaptured} blackCaptured={gc.blackCaptured} evalCp={gc.evalCp} />
      </div>
    </div>
  )
}
