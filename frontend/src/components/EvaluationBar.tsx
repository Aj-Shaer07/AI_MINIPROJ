import { useEffect, useState } from 'react'

type Props = {
  evalCp?: number
  playerColor?: 'white' | 'black'
}

export default function EvaluationBar({ evalCp = 0, playerColor = 'white' }: Props) {
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 768px)')
    const onChange = () => setIsMobile(mq.matches)
    onChange()

    if (typeof mq.addEventListener === 'function') {
      mq.addEventListener('change', onChange)
      return () => mq.removeEventListener('change', onChange)
    }

    mq.addListener(onChange)
    return () => mq.removeListener(onChange)
  }, [])

  // Map centipawns (-1000..+1000) to fill percent (0..100)
  const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v))

  // Evaluation is passed from White's perspective (+cp = White advantage)
  // Calculate relative advantage for the player at the bottom
  const bottomAdvantage = playerColor === 'white' ? evalCp : -evalCp

  const max = 1000
  // normalize to 0..100% where 50% is dead even
  const pct = ((clamp(bottomAdvantage, -max, max) + max) / (2 * max)) * 100

  // Vertical on desktop, horizontal on mobile.
  const fillStyle = {
    ...(isMobile ? { width: `${pct}%` } : { height: `${pct}%` }),
    background: playerColor === 'white' ? 'var(--eval-white)' : 'var(--eval-black)',
  }

  // The background behind the bar
  const topColor = playerColor === 'white' ? 'var(--eval-black)' : 'var(--eval-white)'

  const isBottomAdv = bottomAdvantage >= 0
  const displayVal = Math.abs(evalCp) >= 100
    ? (Math.abs(evalCp) / 100).toFixed(1)
    : (Math.abs(evalCp) / 100).toFixed(2)

  const textColor = isBottomAdv
    ? (playerColor === 'white' ? 'var(--eval-black)' : 'var(--eval-white)')
    : (playerColor === 'white' ? 'var(--eval-white)' : 'var(--eval-black)')

  return (
    <div className={`eval-bar ${isMobile ? 'horizontal' : ''}`} style={{ background: topColor }} aria-hidden>
      <div className={`eval-text ${isBottomAdv ? 'bottom-adv' : 'top-adv'} ${isMobile ? 'mobile' : ''}`} style={{ color: textColor }}>
        {displayVal}
      </div>
      <div className={`eval-fill ${isMobile ? 'horizontal' : ''}`} style={fillStyle} />
    </div>
  )
}
