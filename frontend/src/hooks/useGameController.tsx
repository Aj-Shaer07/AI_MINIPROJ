import { useState, useCallback } from 'react'

export type BoardState = string[][]

export default function useGameController() {
  const initial: BoardState = [
    ['r','n','b','q','k','b','n','r'],
    ['p','p','p','p','p','p','p','p'],
    ['','','','','','','',''],
    ['','','','','','','',''],
    ['','','','','','','',''],
    ['','','','','','','',''],
    ['P','P','P','P','P','P','P','P'],
    ['R','N','B','Q','K','B','N','R'],
  ]

  const [board, setBoard] = useState<BoardState>(initial)
  const [lastMove, setLastMove] = useState<[number,number,number,number] | null>(null)
  const [possibleMoves, setPossibleMoves] = useState<Array<[number,number]>>([])
  const [whiteCaptured, setWhiteCaptured] = useState<string[]>([])
  const [blackCaptured, setBlackCaptured] = useState<string[]>([])
  const [evalCp, setEvalCp] = useState<number>(0)

  const movePiece = useCallback((fromR:number, fromC:number, toR:number, toC:number) => {
    setBoard(prev => {
      const copy = prev.map(r => r.slice())
      const piece = copy[fromR][fromC]
      copy[fromR][fromC] = ''
      // capture
      if (copy[toR][toC]) {
        const captured = copy[toR][toC]
        if (captured === captured.toUpperCase()) {
          setWhiteCaptured(w => [...w, captured])
        } else {
          setBlackCaptured(b => [...b, captured])
        }
      }
      copy[toR][toC] = piece
      setLastMove([fromR, fromC, toR, toC])
      return copy
    })
    // clear possible moves
    setPossibleMoves([])
  }, [])

  return {
    board,
    lastMove,
    possibleMoves,
    whiteCaptured,
    blackCaptured,
    evalCp,
    movePiece,
    setPossibleMoves,
    setEvalCp,
  }
}
