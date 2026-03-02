import './App.css'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Landing from './pages/Landing'
import Game from './pages/Game'

function App() {
  return (
    <BrowserRouter>
      <header className="app-header">
        <div className="brand">
          <Link to="/">Chess UI</Link>
        </div>
        <nav className="app-nav">
          <Link to="/">Home</Link>
          <Link to="/game">Play</Link>
        </nav>
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/game" element={<Game />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}

export default App
