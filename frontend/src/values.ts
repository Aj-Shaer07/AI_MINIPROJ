// ─── Game Configuration & Constants ───

export type GameSettings = {
    timeControl: string
    increment: string
    playerColor: 'white' | 'black'
    showPlayerClock: boolean
    showEngineClock: boolean
}

export const DEFAULT_SETTINGS: GameSettings = {
    timeControl: '5',
    increment: '0',
    playerColor: 'white',
    showPlayerClock: true,
    showEngineClock: false,
}

export type EvalInfo = {
    eval_cp: number
    depth: number
    time_s: number
    nodes: number
    q_nodes: number
    cutoffs: number
    tt_hits: number
    tt_probes: number
    max_ply: number
    max_q_ply: number
    mate_in?: number
}

export const DEFAULT_EVAL_INFO: EvalInfo = {
    eval_cp: 0,
    depth: 0,
    time_s: 0,
    nodes: 0,
    q_nodes: 0,
    cutoffs: 0,
    tt_hits: 0,
    tt_probes: 0,
    max_ply: 0,
    max_q_ply: 0,
}

export const TIME_OPTIONS = [
    { label: '1 min', value: '1' },
    { label: '3 min', value: '3' },
    { label: '5 min', value: '5', default: true },
    { label: '10 min', value: '10' },
]

export const INCREMENT_OPTIONS = [
    { label: '+0s', value: '0', default: true },
    { label: '+1s', value: '1' },
    { label: '+2s', value: '2' },
    { label: '+5s', value: '5' },
]

export const COLOR_OPTIONS = [
    { label: 'White', value: 'white', default: true },
    { label: 'Black', value: 'black' },
]

export const API_BASE_URL = 'http://127.0.0.1:8000';
export const CLOCK_TICK_RATE_MS = 100;
export const CHECK_COLOR = 'radial-gradient(ellipse, rgba(255,0,0,0.8), transparent)';
export const PREMOVE_COLOR = 'rgba(230, 237, 154, 1)';

// ─── Colors (CSS variable references, for use in JS when needed) ───
export const COLORS = {
    bgPrimary: '#121216', // BG_COLOR
    bgSecondary: '#1a1a1e', // PANEL_BG_COLOR
    bgTertiary: '#222226', // PANEL_HEADER_BG
    bgElevated: '#323237', // PANEL_BORDER_COLOR
    boardLight: '#ebd7b4', // LIGHT_COLOR
    boardDark: '#af8460', // DARK_COLOR
    accentGreen: '#54c481', // EVAL_BAR_WHITE_COLOR
    accentRed: '#b43232', // RESIGN_BTN_COLOR
    accentGold: '#e6bc97', // POPUP_ACCENT
    textPrimary: '#ffffff', // PANEL_TITLE_COLOR
    textSecondary: '#d2d2d7', // PANEL_TEXT_COLOR
    textMuted: '#aaaaaa', // LABEL_COLOR
    textDim: '#888888', // (Calculated slightly darker than LABEL_COLOR)
    evalWhite: '#ffffff',
    evalBlack: '#1c1c20', // EVAL_BAR_BG
} as const;

// ─── Piece Symbols ───
export const PIECE_SYMBOLS: Record<string, string> = {
    K: '♔', Q: '♕', R: '♖', B: '♗', N: '♘', P: '♙',
    k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟',
}
