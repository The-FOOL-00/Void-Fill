/**
 * SuggestionOverlay — slide-up bottom sheet with AI suggestions
 *
 * Appears after voice input on the Home screen. Shows 3 suggestion
 * cards with optional reason, supports card selection, accept/skip,
 * auto-TTS readout, backdrop dismiss, and 30s auto-dismiss.
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../api/client'
import { useSpeechOutput } from '../hooks/useSpeechOutput'
import type { VoidSuggestion } from '../types/api'
import styles from './SuggestionOverlay.module.css'

interface Props {
  suggestions: VoidSuggestion[]
  transcript: string
  onClose: () => void
  onAccept: (s: VoidSuggestion) => void
}

const AUTO_DISMISS_MS = 30_000
const TTS_DELAY_MS = 600

// ── Category accent colours (mirrored from HomePage) ──────────────────────
const CATEGORY_COLORS: Record<string, string> = {
  academic: '#ED1C24', study: '#ED1C24',
  career: '#3B82F6', work: '#3B82F6', finance: '#3B82F6',
  health: '#10B981', wellness: '#10B981', fitness: '#10B981',
  personal: '#A855F7',
  default: '#6B7280',
}

function accentFor(title: string): string {
  const key = title.toLowerCase()
  for (const [cat, color] of Object.entries(CATEGORY_COLORS)) {
    if (key.includes(cat)) return color
  }
  return CATEGORY_COLORS.default
}

export default function SuggestionOverlay({ suggestions, transcript, onClose, onAccept }: Props) {
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null)
  const [visible, setVisible] = useState(false)
  const { speak, cancel: cancelTTS } = useSpeechOutput()
  const autoDismissRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const ttsRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ── Mount animation ────────────────────────────────────────────────────
  useEffect(() => {
    // Trigger slide-up on next frame
    requestAnimationFrame(() => setVisible(true))

    // TTS auto-read after 600ms
    ttsRef.current = setTimeout(() => {
      if (suggestions.length > 0) {
        const lines = suggestions.map((s, i) => `${i + 1}: ${s.title}.`).join(' ')
        speak(`Here are three suggestions. ${lines}`)
      }
    }, TTS_DELAY_MS)

    // Auto-dismiss after 30s
    autoDismissRef.current = setTimeout(() => {
      handleDismiss()
    }, AUTO_DISMISS_MS)

    return () => {
      if (ttsRef.current) clearTimeout(ttsRef.current)
      if (autoDismissRef.current) clearTimeout(autoDismissRef.current)
      cancelTTS()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Dismiss (skip all) ────────────────────────────────────────────────
  const handleDismiss = useCallback(() => {
    cancelTTS()
    const ids = suggestions
      .map((s) => s.goal_id)
      .filter((id): id is string => id !== null)
    if (ids.length > 0) {
      api.suggestions.skip(ids).catch(() => null)
    }
    setVisible(false)
    // Wait for slide-out animation before unmounting
    setTimeout(onClose, 300)
  }, [suggestions, onClose, cancelTTS])

  // ── Accept selected ───────────────────────────────────────────────────
  const handleAccept = useCallback(() => {
    if (selectedIdx === null) return
    cancelTTS()
    const selected = suggestions[selectedIdx]
    if (selected.goal_id) {
      api.suggestions.accept(selected.goal_id).catch(() => null)
    }
    speak('Good choice. Go for it.')
    setVisible(false)
    setTimeout(() => onAccept(selected), 300)
  }, [selectedIdx, suggestions, onAccept, cancelTTS, speak])

  // ── Backdrop click = "Not now" ────────────────────────────────────────
  const handleBackdropClick = useCallback(() => {
    handleDismiss()
  }, [handleDismiss])

  return (
    <div
      className={`${styles.backdrop} ${visible ? styles.backdropVisible : ''}`}
      onClick={handleBackdropClick}
    >
      <div
        className={`${styles.sheet} ${visible ? styles.sheetVisible : ''}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <h2 className={styles.heading}>Here&rsquo;s what I&rsquo;d suggest</h2>
        {transcript && (
          <p className={styles.transcript}>&ldquo;{transcript}&rdquo;</p>
        )}

        {/* Suggestion cards */}
        <div className={styles.cardList}>
          {suggestions.map((s, i) => {
            const isSelected = selectedIdx === i
            const isFaded = selectedIdx !== null && !isSelected
            return (
              <button
                key={s.goal_id ?? i}
                className={`${styles.card} ${isSelected ? styles.cardSelected : ''} ${isFaded ? styles.cardFaded : ''}`}
                style={{ '--accent': accentFor(s.title) } as React.CSSProperties}
                onClick={() => setSelectedIdx(i)}
              >
                <div className={styles.cardAccent} />
                <div className={styles.cardBody}>
                  <p className={styles.cardTitle}>
                    {isSelected && <span className={styles.check}>✓ </span>}
                    {s.title}
                  </p>
                  {s.reason && <p className={styles.cardReason}>{s.reason}</p>}
                  <p className={styles.cardScore}>
                    Score {Math.round(s.score * 100)}%
                  </p>
                </div>
              </button>
            )
          })}
        </div>

        {/* Actions */}
        <div className={styles.actions}>
          <button
            className={styles.acceptBtn}
            disabled={selectedIdx === null}
            onClick={handleAccept}
          >
            Let&rsquo;s do it
          </button>
          <button className={styles.skipBtn} onClick={handleDismiss}>
            Not now
          </button>
        </div>
      </div>
    </div>
  )
}
