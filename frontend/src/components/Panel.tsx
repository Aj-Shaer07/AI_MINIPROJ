import CapturedBar from './CapturedBar'

type Props = {
  whiteCaptured: string[]
  blackCaptured: string[]
  evalCp?: number
}

export default function Panel({ whiteCaptured, blackCaptured, evalCp = 0 }: Props) {
  return (
    <aside className="side-panel">
      <div className="eval-box">
        <h3>Evaluation</h3>
        <div className="eval-value">{evalCp} cp</div>
      </div>

      <CapturedBar captured={whiteCaptured} label="White Captured" />
      <CapturedBar captured={blackCaptured} label="Black Captured" />

      <div className="moves-log">
        <h4>Moves</h4>
        <div className="moves-list">(move list will appear here)</div>
      </div>

      <button className="resign-btn">Resign</button>
    </aside>
  )
}
