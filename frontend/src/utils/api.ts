const BACKEND_URL = "/api"


function getArenaSessionId(): string {
  const key = 'arena_session_id'
  const existing = localStorage.getItem(key)
  if (existing) return existing

  const sessionId =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`

  localStorage.setItem(key, sessionId)
  return sessionId
}


function jsonHeaders(includeArenaSession = false): HeadersInit {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (includeArenaSession) {
    headers['X-Session-Id'] = getArenaSessionId()
  }
  return headers
}

export async function searchBestMove(fen: string, history: string[] = [], max_depth = 3, engine_is_black = true, botId?: string) {
  const body: any = { fen, history, max_depth, engine_is_black }
  if (botId) {
    body.bot_id = botId
  }
  const res = await fetch(`${BACKEND_URL}/search`, {
    method: 'POST',
    headers: jsonHeaders(),
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
    headers: jsonHeaders(),
  })
  if (!res.ok) throw new Error(`Get bots failed: ${res.status}`)
  return res.json()
}

export async function evaluatePosition(fen: string, history: string[] = [], ply = 0, is_engine_move = false) {
  const res = await fetch(`${BACKEND_URL}/evaluate`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ fen, history, ply, is_engine_move }),
  })
  if (!res.ok) throw new Error(`Evaluate request failed: ${res.status}`)
  return res.json()
}

export async function generateMoves(fen: string, history: string[] = []) {
  const res = await fetch(`${BACKEND_URL}/generate_moves`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ fen, history }),
  })
  if (!res.ok) throw new Error(`Generate moves failed: ${res.status}`)
  return res.json()
}

export interface AnalysisPly {
  ply: number
  move: string
  move_uci: string
  eval_cp: number
  eval_diff: number
  annotation: 'BRILLIANT' | 'GOOD' | 'NEUTRAL' | 'INACCURACY' | 'MISTAKE' | 'BLUNDER' | 'ENGINE'
  annotation_symbol: string
  annotation_color: string
  best_move_san: string | null
  best_move_uci: string | null
  is_player_move: boolean
  explanation_text: string | null
}

export async function analyzeGame(history: string[], playerIsWhite = true): Promise<{ analysis: AnalysisPly[] }> {
  const res = await fetch(`${BACKEND_URL}/analyze_game`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ history, player_is_white: playerIsWhite }),
  })
  if (!res.ok) throw new Error(`Analyze game failed: ${res.status}`)
  return res.json()
}
export interface ArenaSession {
  depth: number
  quality_tier: number
  games_played: number
  wins: number
  losses: number
  draws: number
  estimated_elo: number
  calibrated: boolean
  draw_streak: number
}

export async function arenaGetSession(): Promise<ArenaSession> {
  const res = await fetch(`${BACKEND_URL}/arena/session`, {
    headers: jsonHeaders(true),
  })
  if (!res.ok) throw new Error(`Arena session failed: ${res.status}`)
  return res.json()
}

export async function arenaReportResult(
  result: 'win' | 'loss' | 'draw'
): Promise<{ result: string; message: string; estimated_elo: number; next: { depth: number; quality_tier: number }; session: ArenaSession }> {
  const res = await fetch(`${BACKEND_URL}/arena/result`, {
    method: 'POST',
    headers: jsonHeaders(true),
    body: JSON.stringify({ result }),
  })
  if (!res.ok) throw new Error(`Arena result failed: ${res.status}`)
  return res.json()
}

export async function arenaResetSession(): Promise<{ reset: boolean; session: ArenaSession }> {
  const res = await fetch(`${BACKEND_URL}/arena/reset`, {
    method: 'POST',
    headers: jsonHeaders(true),
  })
  if (!res.ok) throw new Error(`Arena reset failed: ${res.status}`)
  return res.json()
}

export async function arenaSearch(
  fen: string,
  history: string[],
  depth: number,
  quality_tier: number,
  engine_is_black: boolean
): Promise<{ best_move: string | null; info: Record<string, unknown> }> {
  const res = await fetch(`${BACKEND_URL}/arena/search`, {
    method: 'POST',
    headers: jsonHeaders(true),
    body: JSON.stringify({ fen, history, depth, quality_tier, engine_is_black }),
  })
  if (!res.ok) throw new Error(`Arena search failed: ${res.status}`)
  return res.json()
}
