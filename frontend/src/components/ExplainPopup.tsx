import { useEffect, useState } from 'react'
import { EXPLANATION_DURATION_MS } from '../values'
import Piece from './Piece'

export type ExplanationData = {
    text: string
    piece: string
}

type Props = {
    explanationData: ExplanationData | null
}

export default function ExplainPopup({ explanationData }: Props) {
    const [visibleData, setVisibleData] = useState<ExplanationData | null>(null)
    const [isDismissing, setIsDismissing] = useState(false)

    useEffect(() => {
        if (explanationData) {
            setVisibleData(explanationData)
            setIsDismissing(false)
            const timer = setTimeout(() => {
                setIsDismissing(true)
            }, EXPLANATION_DURATION_MS)
            return () => clearTimeout(timer)
        } else {
            setIsDismissing(true)
        }
    }, [explanationData])

    const handleAnimationEnd = () => {
        if (isDismissing) {
            setVisibleData(null)
            setIsDismissing(false)
        }
    }

    if (!visibleData) return null

    const text = visibleData.text
    const pieceCode = visibleData.piece

    return (
        <div
            className={`horse-popup ${isDismissing ? 'dismiss' : ''}`}
            onAnimationEnd={handleAnimationEnd}
        >
            <div className="horse-bubble">
                {text}
            </div>
            <div className="horse-avatar">
                <div className="piece-wrapper">
                    <Piece code={pieceCode} />
                </div>
            </div>
        </div>
    )
}
