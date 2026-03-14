import { useEffect, useRef } from 'react'
import type { AnalysisPly } from '../utils/api'

interface Props {
  analysis: AnalysisPly[]
  currentPly: number
  onPlyClick: (ply: number) => void
}

export default function AnnotatedMoveList({ analysis, currentPly, onPlyClick }: Props) {
  const listRef = useRef<HTMLDivElement>(null)
  const activeRef = useRef<HTMLButtonElement>(null)

  // Auto-scroll active move into view
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [currentPly])

  // Group moves into pairs (white + black per row)
  const pairs: [AnalysisPly, AnalysisPly | null][] = []
  for (let i = 0; i < analysis.length; i += 2) {
    pairs.push([analysis[i], analysis[i + 1] ?? null])
  }

  const badgeStyle = (color: string) => ({
    display: 'inline-block',
    fontSize: '10px',
    fontWeight: 700,
    color,
    lineHeight: 1,
    minWidth: '16px',
    textAlign: 'center' as const,
  })

  const MoveBtn = ({ ply }: { ply: AnalysisPly }) => {
    const isActive = currentPly === ply.ply
    return (
      <button
        ref={isActive ? activeRef : undefined}
        className={`analysis-move-btn ${isActive ? 'active' : ''}`}
        onClick={() => onPlyClick(ply.ply)}
        title={ply.annotation !== 'NEUTRAL' && ply.annotation !== 'ENGINE'
          ? `${ply.annotation}${ply.annotation_symbol ? ' ' + ply.annotation_symbol : ''}`
          : undefined}
      >
        <span>{ply.move}</span>
        {ply.annotation_symbol && (
          <span style={badgeStyle(ply.annotation_color)}>{ply.annotation_symbol}</span>
        )}
      </button>
    )
  }

  return (
    <div className="annotated-move-list" ref={listRef}>
      {pairs.map(([white, black], idx) => (
        <div key={idx} className="move-pair-row">
          <span className="move-number">{idx + 1}.</span>
          <MoveBtn ply={white} />
          {black ? <MoveBtn ply={black} /> : <span className="move-placeholder" />}
        </div>
      ))}
    </div>
  )
}
