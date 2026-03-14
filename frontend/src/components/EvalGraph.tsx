
interface Props {
  evals: number[]         // eval_cp per ply (index 0 = after move 1)
  currentPly: number      // 0-indexed current ply (0 = start, 1 = after move 1)
  onPlyClick: (ply: number) => void  // callback with 1-based ply number
}

const CLAMP = 1200  // cp value that fills the bar completely

function normalize(cp: number) {
  // Map cp → 0–100 (50 = equal)
  const clamped = Math.max(-CLAMP, Math.min(CLAMP, cp))
  return 50 - (clamped / CLAMP) * 50
}

export default function EvalGraph({ evals, currentPly, onPlyClick }: Props) {
  const W = 320
  const H = 160
  const PAD = { t: 12, b: 24, l: 32, r: 12 }
  const innerW = W - PAD.l - PAD.r
  const innerH = H - PAD.t - PAD.b
  const n = evals.length

  if (n === 0) return null

  // Map ply index → x, y pixel coords
  const px = (i: number) => PAD.l + (i / Math.max(n - 1, 1)) * innerW
  const py = (cp: number) => PAD.t + (normalize(cp) / 100) * innerH

  // Build polyline points
  const pts = evals.map((cp, i) => `${px(i)},${py(cp)}`).join(' ')

  // Area fill path (down to the midline then back)
  const midY = py(0)
  const areaPath =
    `M ${px(0)} ${midY} ` +
    evals.map((cp, i) => `L ${px(i)} ${py(cp)}`).join(' ') +
    ` L ${px(n - 1)} ${midY} Z`

  // Current ply x position (currentPly 0 = start, no line; else after move currentPly)
  const indicatorX = currentPly > 0 ? px(currentPly - 1) : null

  // Y-axis labels
  const yLabels = ['+10', '+5', '0', '-5', '-10']
  const yCps = [1000, 500, 0, -500, -1000]

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      style={{ display: 'block', userSelect: 'none', cursor: 'pointer' }}
      onClick={(e) => {
        const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect()
        const relX = (e.clientX - rect.left) / rect.width * W
        const idx = Math.round(((relX - PAD.l) / innerW) * (n - 1))
        const clamped = Math.max(0, Math.min(n - 1, idx))
        onPlyClick(clamped + 1)
      }}
    >
      {/* Background */}
      <rect x={PAD.l} y={PAD.t} width={innerW} height={innerH} fill="#1a1a1e" rx="4" />

      {/* Midline */}
      <line x1={PAD.l} y1={midY} x2={PAD.l + innerW} y2={midY} stroke="#555" strokeWidth="1" strokeDasharray="4 3" />

      {/* Y grid lines + labels */}
      {yCps.map((cp, i) => {
        const y = py(cp)
        return (
          <g key={cp}>
            <line x1={PAD.l} y1={y} x2={PAD.l + innerW} y2={y} stroke="#2a2a2e" strokeWidth="0.5" />
            <text x={PAD.l - 4} y={y + 4} textAnchor="end" fontSize="9" fill="#666">{yLabels[i]}</text>
          </g>
        )
      })}

      {/* Shaded area — white advantage above midline (green), black advantage below (red) */}
      <clipPath id="above">
        <rect x={PAD.l} y={PAD.t} width={innerW} height={midY - PAD.t} />
      </clipPath>
      <clipPath id="below">
        <rect x={PAD.l} y={midY} width={innerW} height={PAD.t + innerH - midY} />
      </clipPath>
      <path d={areaPath} fill="rgba(84,196,129,0.25)" clipPath="url(#above)" />
      <path d={areaPath} fill="rgba(180,50,50,0.25)" clipPath="url(#below)" />

      {/* Eval line */}
      <polyline points={pts} fill="none" stroke="#54c481" strokeWidth="1.8" strokeLinejoin="round" />

      {/* Dots per ply */}
      {evals.map((cp, i) => (
        <circle key={i} cx={px(i)} cy={py(cp)} r="2.5"
          fill={i + 1 === currentPly ? '#fff' : '#54c481'}
          stroke={i + 1 === currentPly ? '#54c481' : 'none'}
          strokeWidth="1.5"
        />
      ))}

      {/* Current ply indicator */}
      {indicatorX !== null && (
        <line x1={indicatorX} y1={PAD.t} x2={indicatorX} y2={PAD.t + innerH}
          stroke="rgba(255,255,255,0.6)" strokeWidth="1.5" strokeDasharray="4 2" />
      )}

      {/* X-axis label */}
      <text x={PAD.l + innerW / 2} y={H - 4} textAnchor="middle" fontSize="9" fill="#555">Moves</text>
    </svg>
  )
}
