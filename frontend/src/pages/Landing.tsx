import { Link } from 'react-router-dom'
import '../styles/chess.css'

export default function Landing() {
  return (
    <div className="landing">
      <div className="landing-card">
        <h1>Welcome to Chess UI</h1>
        <p>A clean, modular React chess interface — UI only.</p>
        <div className="landing-actions">
          <Link to="/game" className="btn">Start Playing</Link>
        </div>
      </div>
    </div>
  )
}
