import { PIECE_SYMBOLS } from '../values'

type Props = { code: string }

export default function Piece({ code }: Props) {
  const isWhite = code === code.toUpperCase()
  const char = PIECE_SYMBOLS[code] || code

  return (
    <div className={`piece ${isWhite ? 'white' : 'black'}`}>
      {char}
    </div>
  )
}
