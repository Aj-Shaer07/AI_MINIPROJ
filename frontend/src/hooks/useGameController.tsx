import { useState, useCallback, useEffect, useRef } from 'react'
import { Chess, Move } from 'chess.js'
import { searchBestMove, evaluatePosition, arenaSearch } from '../utils/api'

export type BoardState = string[][]

type UseGameControllerOpts = {
  playerColor?: 'white' | 'black'
  maxDepth?: number
  timeControlMin?: number
  incrementSec?: number
  enableCoachMode?: boolean
  enableClocks?: boolean
  botId?: string
  isArena?: boolean
  arenaDepth?: number
  arenaQuality?: number
}

export type GameOverReason = 'checkmate' | 'stalemate' | 'time' | 'resign' | null

// Convert chess.js FEN placement to 2D board array
const fenToBoard = (fen: string): BoardState => {
  const [placement] = fen.split(' ')
  return placement.split('/').map(row => {
    const cells: string[] = []
    for (const ch of row) {
      const n = parseInt(ch)
      if (!isNaN(n)) for (let i = 0; i < n; i++) cells.push('')
      else cells.push(ch)
    }
    return cells
  })
}

const squareToCoords = (sq: string): [number, number] => [8 - parseInt(sq[1]), sq.charCodeAt(0) - 97]
const coordsToSquare = (r: number, c: number) => `${String.fromCharCode(97 + c)}${8 - r}`

export default function useGameController(opts: UseGameControllerOpts = {}) {
  const { 
    playerColor = 'white', 
    maxDepth = 3, 
    timeControlMin = 5, 
    incrementSec = 0, 
    enableCoachMode = false, 
    enableClocks = false, 
    botId,
    isArena = false,
    arenaDepth = 4,
    arenaQuality = 0
  } = opts

  // The single source of truth chess instance lives in a ref so effects always read
  // the latest game without stale closures.
  const gameRef = useRef(new Chess())

  // Accumulated move history — we append each SAN string as moves happen.
  // Keeping in a ref means the async engine callback always reads latest value.
  const historyRef = useRef<string[]>([])

  // Derived display state — driven from gameRef on every mutation
  const [board, setBoard] = useState<BoardState>(fenToBoard(gameRef.current.fen()))
  const [lastMove, setLastMove] = useState<[number, number, number, number] | null>(null)
  const [possibleMoves, setPossibleMoves] = useState<Array<[number, number]>>([])
  const [pendingPromotion, setPendingPromotion] = useState<{ from: string; to: string; toCoords: [number, number] } | null>(null)
  const [evalCp, setEvalCp] = useState<number>(0)
  const [evalInfo, setEvalInfo] = useState<any>(null)
  // Split history into a plain string array — we keep our own copy so React always
  // sees a new reference and re-renders the Panel.
  const [moveHistory, setMoveHistory] = useState<string[]>([])
  const [turn, setTurn] = useState<'white' | 'black'>('white')
  const [inCheckCoord, setInCheckCoord] = useState<[number, number] | null>(null)
  const [gameOverReason, setGameOverReason] = useState<GameOverReason>(null)
  const [whiteTime, setWhiteTime] = useState(timeControlMin * 60 * 1000)
  const [blackTime, setBlackTime] = useState(timeControlMin * 60 * 1000)
  const [explanationData, setExplanationData] = useState<{ text: string, piece: string } | null>(null)

  // Premove stored as a ref so the async engine callback always reads the latest value
  // without needing to be in the effect dependency array.
  const premoveRef = useRef<{ from: string; to: string } | null>(null)
  // Also expose as state so the Chessboard can display the highlight
  const [premove, setPremoveState] = useState<{ from: string; to: string } | null>(null)

  const setPremove = (val: { from: string; to: string } | null) => {
    premoveRef.current = val
    setPremoveState(val)
  }

  // ─── Helpers ─────────────────────────────────────────────────────────────

  const syncDisplayState = (g: Chess, moved: Move) => {
    setBoard(fenToBoard(g.fen()))
    const f = squareToCoords(moved.from)
    const t = squareToCoords(moved.to)
    setLastMove([f[0], f[1], t[0], t[1]])
    setTurn(g.turn() === 'w' ? 'white' : 'black')
    // Append the SAN of the just-played move to the accumulated history
    historyRef.current = [...historyRef.current, moved.san]
    setMoveHistory([...historyRef.current])

    // Always clear the old explanation on every move so the ExplainPopup
    // useEffect always sees null → new value, which guarantees it re-triggers.
    setExplanationData(null)

    // Check / checkmate detection
    if (g.isCheck()) {
      const targetKing = g.turn() === 'w' ? 'K' : 'k'
      const b = fenToBoard(g.fen())
      outer: for (let r = 0; r < 8; r++)
        for (let c = 0; c < 8; c++)
          if (b[r][c] === targetKing) { setInCheckCoord([r, c]); break outer }
    } else {
      setInCheckCoord(null)
    }

    // Game over detection
    if (g.isCheckmate()) setGameOverReason('checkmate')
    else if (g.isStalemate() || g.isDraw()) setGameOverReason('stalemate')
  }

  // ─── Clock effect ─────────────────────────────────────────────────────────
  const turnRef = useRef(turn)
  turnRef.current = turn

  useEffect(() => {
    if (gameOverReason || !enableClocks) return
    const id = window.setInterval(() => {
      if (turnRef.current === 'white') {
        setWhiteTime(t => {
          if (t <= 100) { setGameOverReason('time'); return 0 }
          return t - 100
        })
      } else {
        setBlackTime(t => {
          if (t <= 100) { setGameOverReason('time'); return 0 }
          return t - 100
        })
      }
    }, 100)
    return () => clearInterval(id)
  }, [gameOverReason])

  // ─── Eval effect (fire on every half move) ───────────────────────────────
  useEffect(() => {
    if (moveHistory.length === 0) return

    const fen = gameRef.current.fen()
    if (fen === new Chess().fen()) return

    // The player's move corresponds to odd lengths if playing white, even lengths if playing black
    const isPlayerMove = playerColor === 'white' ? moveHistory.length % 2 !== 0 : moveHistory.length % 2 === 0

    const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    evaluatePosition(START_FEN, historyRef.current, 0, !isPlayerMove).then(res => {
      setEvalCp(res.score_cp)
      if (enableCoachMode && res.explanation) {
        // Always show explanations for player moves and engine moves equally
        setExplanationData({ text: res.explanation.text, piece: res.explanation.piece })
      }
    }).catch(() => { })
  }, [moveHistory.length, enableCoachMode, playerColor]) // re-run every time a new half-move is appended

  // ─── Engine turn effect ───────────────────────────────────────────────────
  // We use a flag + abort pattern to prevent stale async calls.
  useEffect(() => {
    const isEngineTurn = turn !== playerColor
    if (!isEngineTurn || gameOverReason || gameRef.current.isGameOver()) return

    let cancelled = false
    const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

      ; (async () => {
        try {
          let resp;
          if (isArena) {
            resp = await arenaSearch(START_FEN, historyRef.current, arenaDepth, arenaQuality, playerColor === 'white')
          } else {
            resp = await searchBestMove(START_FEN, historyRef.current, maxDepth, playerColor === 'white', botId)
          }
          if (cancelled || !resp?.best_move) return

          // Validate & apply engine move
          const g = new Chess(gameRef.current.fen())
          const move = g.move({
            from: resp.best_move.slice(0, 2),
            to: resp.best_move.slice(2, 4),
            promotion: resp.best_move[4] || 'q',
          })
          gameRef.current = g
          syncDisplayState(g, move)
          setEvalInfo(resp.info)
          // Engine side explanation is removed entirely.

          // Increment for engine side
          if (playerColor === 'white') setBlackTime(t => t + incrementSec * 1000)
          else setWhiteTime(t => t + incrementSec * 1000)

          // Fire premove immediately — read from ref, not stale closure
          const pm = premoveRef.current
          if (pm) {
            setPremove(null)
            setPossibleMoves([])
            try {
              const pg = new Chess(g.fen())
              const pmMove = pg.move({ from: pm.from, to: pm.to, promotion: 'q' })
              gameRef.current = pg
              syncDisplayState(pg, pmMove)
              // Increment for player side
              if (playerColor === 'white') setWhiteTime(t => t + incrementSec * 1000)
              else setBlackTime(t => t + incrementSec * 1000)
            } catch {
              // Premove was illegal — silently discard
            }
          }
        } catch (e) {
          if (!cancelled) console.error('Engine search failed', e)
        }
      })()

    return () => { cancelled = true }
  }, [turn, gameOverReason, moveHistory.length])

  // ─── Actions ──────────────────────────────────────────────────────────────

  const getLegalMoves = useCallback(async (r: number, c: number): Promise<Array<[number, number]>> => {
    if (gameOverReason) return []
    const sq = coordsToSquare(r, c)
    let g = gameRef.current

    // Out-of-turn: temporarily flip the turn token to compute pseudo-legal moves
    if (g.turn() !== playerColor[0]) {
      try {
        const clone = new Chess(g.fen())
        const tokens = clone.fen().split(' ')
        tokens[1] = tokens[1] === 'w' ? 'b' : 'w'
        tokens[3] = '-'
        clone.load(tokens.join(' '))
        g = clone
      } catch {
        return []
      }
    }

    return (g.moves({ square: sq as any, verbose: true }) as Move[]).map(m => squareToCoords(m.to))
  }, [gameOverReason, playerColor])

  const movePiece = useCallback(async (fromR: number, fromC: number, toR: number, toC: number) => {
    if (gameOverReason) return

    // Queue a premove if it's not our turn
    if (turn !== playerColor) {
      setPremove({ from: coordsToSquare(fromR, fromC), to: coordsToSquare(toR, toC) })
      return
    }

    const fromSq = coordsToSquare(fromR, fromC)
    const toSq = coordsToSquare(toR, toC)

    // Check if this is a promotion move
    const g = new Chess(gameRef.current.fen())
    const legalMoves = g.moves({ square: fromSq as any, verbose: true })
    const isPromo = legalMoves.some(m => m.to === toSq && m.promotion)
    if (isPromo) {
      setPendingPromotion({ from: fromSq, to: toSq, toCoords: [toR, toC] })
      return
    }

    try {
      const move = g.move({ from: fromSq, to: toSq })
      gameRef.current = g
      syncDisplayState(g, move)
      if (playerColor === 'white') setWhiteTime(t => t + incrementSec * 1000)
      else setBlackTime(t => t + incrementSec * 1000)
    } catch {
      console.warn('Illegal move attempted')
    }
  }, [turn, playerColor, incrementSec, gameOverReason])

  const confirmPromotion = useCallback((piece: 'q' | 'r' | 'b' | 'n') => {
    if (!pendingPromotion) return
    try {
      const g = new Chess(gameRef.current.fen())
      const move = g.move({ from: pendingPromotion.from, to: pendingPromotion.to, promotion: piece })
      gameRef.current = g
      syncDisplayState(g, move)
      if (playerColor === 'white') setWhiteTime(t => t + incrementSec * 1000)
      else setBlackTime(t => t + incrementSec * 1000)
    } catch {
      console.warn('Illegal promotion attempted')
    }
    setPendingPromotion(null)
  }, [pendingPromotion, playerColor, incrementSec])

  const cancelPromotion = useCallback(() => setPendingPromotion(null), [])

  const resign = useCallback(() => setGameOverReason('resign'), [])
  const clearPremove = useCallback(() => setPremove(null), [])

  return {
    board,
    lastMove,
    possibleMoves,
    evalCp,
    evalInfo,
    moveHistory,
    turn,
    whiteTime,
    blackTime,
    inCheckCoord,
    premove,
    gameOverReason,
    explanationData,
    pendingPromotion,
    setPossibleMoves,
    getLegalMoves,
    movePiece,
    confirmPromotion,
    cancelPromotion,
    clearPremove,
    resign,
  }
}
