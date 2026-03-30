import './App.css'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Landing from './pages/Landing'
import Game from './pages/Game'
import Analysis from './pages/Analysis'
import Arena from './pages/Arena'

function App() {
  return (
    <BrowserRouter>
      <header className="app-header">
        <div className="brand">
          <Link to="/" state={{ reset: true }}>Chess AI</Link>
        </div>
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/game" element={<Game />} />
          <Route path="/analysis" element={<Analysis />} />
          <Route path="/arena" element={<Arena />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}

export default App
