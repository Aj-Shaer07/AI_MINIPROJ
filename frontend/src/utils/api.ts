const BACKEND_URL = "http://127.0.0.1:8000"

export async function searchBestMove(fen: string, history: string[] = [], max_depth = 3, engine_is_black = true, botId?: string) {
  const body: any = { fen, history, max_depth, engine_is_black }
  if (botId) {
    body.bot_id = botId
  }
  const res = await fetch(`${BACKEND_URL}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(`Search request failed: ${res.status}`)
  }
  return res.json()
}

export interface Bot {
  id: string;
  name: string;
  elo: string;
}

export async function getBots(): Promise<{ bots: Bot[] }> {
  const res = await fetch(`${BACKEND_URL}/bots`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) throw new Error(`Get bots failed: ${res.status}`)
  return res.json()
}

export async function evaluatePosition(fen: string, history: string[] = [], ply = 0, is_engine_move = false) {
  const res = await fetch(`${BACKEND_URL}/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fen, history, ply, is_engine_move }),
  })
  if (!res.ok) throw new Error(`Evaluate request failed: ${res.status}`)
  return res.json()
}

export async function generateMoves(fen: string, history: string[] = []) {
  const res = await fetch(`${BACKEND_URL}/generate_moves`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fen, history }),
  })
  if (!res.ok) throw new Error(`Generate moves failed: ${res.status}`)
  return res.json()
}
