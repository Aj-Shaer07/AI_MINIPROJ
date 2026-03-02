type Props = { evalCp?: number }

export default function EvaluationBar({ evalCp = 0 }: Props) {
  // Map centipawns (-5000..+5000) to fill percent (0..100)
  const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v))
  const max = 5000
  const pct = ((clamp(evalCp, -max, max) + max) / (2 * max)) * 100
  const whitePct = pct
  const blackPct = 100 - pct
  const whiteStyle = { height: `${whitePct}%` }
  const blackStyle = { height: `${blackPct}%` }

  return (
    <div className="eval-bar" aria-hidden>
      <div className="eval-white" style={whiteStyle} />
      <div className="eval-black" style={blackStyle} />
    </div>
  )
}
