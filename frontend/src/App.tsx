import './App.css'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Landing from './pages/Landing'
import Game from './pages/Game'

function App() {
  return (
    <BrowserRouter>
      <header className="app-header">
        <div className="brand">
          <Link to="/">Chess AI</Link>
        </div>
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
