import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../api/client'
import { useVoiceContext } from '../context/VoiceContext'
import { useSpeechOutput } from '../hooks/useSpeechOutput'
import type { VoidNowResponse, VoidSuggestion, Suggestion, AutonomyLogEntry } from '../types/api'
import styles from './HomePage.module.css'

// ── Helpers ───────────────────────────────────────────────────────────────────
function getGreeting(): string {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

function formatDuration(mins: number): string {
  if (mins >= 60) {
    const h = Math.floor(mins / 60)
    const m = mins % 60
    return m > 0 ? `${h}h ${m}m` : `${h}h`
  }
  return `${mins} mins`
}

function formatLogTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

function deriveCategoryFromTitle(title: string): string {
  const t = title.toLowerCase()
  if (t.includes('study') || t.includes('academic') || t.includes('review') || t.includes('lecture')) return 'academic'
  if (t.includes('work') || t.includes('career') || t.includes('finance') || t.includes('apply')) return 'career'
  if (t.includes('health') || t.includes('gym') || t.includes('rest') || t.includes('sleep') || t.includes('exercise')) return 'health'
  return 'personal'
}

function SmallLightningIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="#ED1C24" stroke="none">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  )
}

const CATEGORY_COLORS: Record<string, string> = {
  academic: '#ED1C24',
  study:    '#ED1C24',
  career:   '#3B82F6',
  work:     '#3B82F6',
  finance:  '#3B82F6',
  health:   '#10B981',
  wellness: '#10B981',
  fitness:  '#10B981',
  personal: '#A855F7',
  default:  '#6B7280',
}

function accentColor(title: string): string {
  const key = title.toLowerCase()
  for (const [cat, color] of Object.entries(CATEGORY_COLORS)) {
    if (key.includes(cat)) return color
  }
  return CATEGORY_COLORS.default
}

/** Convert a backend Suggestion (from POST /suggestions/request) to our VoidSuggestion shape */
function toVoidSuggestion(s: Suggestion): VoidSuggestion {
  return {
    id: s.id,
    goal_id: s.goal_id,
    title: s.text || 'Suggestion',
    score: s.score ?? 0,
    reason: undefined,
  }
}

// ── Sub-icons ──────────────────────────────────────────────────────────────────
function SuggestionIcon({ title }: { title: string }) {
  const t = title.toLowerCase()
  const stroke = '#cccccc'
  const size = 20

  if (t.includes('academic') || t.includes('study')) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" />
      </svg>
    )
  }
  if (t.includes('career') || t.includes('work') || t.includes('finance')) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
        <polyline points="17 6 23 6 23 12" />
      </svg>
    )
  }
  if (t.includes('health') || t.includes('wellness') || t.includes('fitness')) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
      </svg>
    )
  }
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={stroke} stroke="none">
      <path d="M12 2l2.09 6.26L20 10l-5.91 1.74L12 18l-2.09-6.26L4 10l5.91-1.74L12 2z" />
    </svg>
  )
}

function PulseIcon() {
  return (
    <svg
      width="18" height="18" viewBox="0 0 24 24" fill="none"
      stroke="#ED1C24" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
      style={{ display: 'inline', verticalAlign: 'middle', marginLeft: 4 }}
    >
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  )
}

// ── Recording flow phases ──────────────────────────────────────────────────
type MicPhase = 'idle' | 'listening' | 'processing' | 'done'

// ── Main Component ─────────────────────────────────────────────────────────────

export default function HomePage() {
  const voice = useVoiceContext()
  const [voidNow, setVoidNow] = useState<VoidNowResponse | null>(null)
  const [suggestions, setSuggestions] = useState<VoidSuggestion[]>([])
  const [micPhase, setMicPhase] = useState<MicPhase>('idle')

  // Overlay state — will be consumed by SuggestionOverlay (Part 3)
  const [overlayOpen, setOverlayOpen] = useState(false)
  const [overlaySuggestions, setOverlaySuggestions] = useState<VoidSuggestion[]>([])
  const [overlayTranscript, setOverlayTranscript] = useState('')

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const RECORDER_ID = 'home-mic'

  // ── Autonomy state ─────────────────────────────────────────────────
  const [autonomyEnabled] = useState(() => localStorage.getItem('autonomyEnabled') !== 'false')
  const [autonomyLog, setAutonomyLog] = useState<AutonomyLogEntry[]>(() => {
    try {
      const stored = localStorage.getItem('autonomyLog')
      if (!stored) return []
      const entries: AutonomyLogEntry[] = JSON.parse(stored)
      const today = new Date().toDateString()
      return entries
        .filter((e) => new Date(e.scheduled_at).toDateString() === today)
        .slice(0, 5)
    } catch { return [] }
  })
  const [autonomyLoading, setAutonomyLoading] = useState(false)
  const [autonomyStatus, setAutonomyStatus] = useState('')
  const { speak } = useSpeechOutput()

  // On mount: load void/now which returns status + void_slot + pre-ranked suggestions
  useEffect(() => {
    api.void.now()
      .then((data) => {
        setVoidNow(data)
        if (data.suggestions.length > 0) {
          setSuggestions(data.suggestions.slice(0, 3))
        }
      })
      .catch(() => null)
  }, [])

  // Watch for voice context audioBlob → process it
  useEffect(() => {
    if (voice.state !== 'stopped' || !voice.audioBlob || voice.activeRecorderId !== RECORDER_ID) return

    // Upload → poll → fetch suggestions
    const processAudio = async () => {
      setMicPhase('processing')
      try {
        const { job_id } = await api.voice.upload(voice.audioBlob!)

        // Poll for transcript (accept both 'completed' and 'partial')
        let transcript = ''
        let attempts = 0
        const maxAttempts = 60   // 60 × 2s = 120s max wait

        await new Promise<void>((resolve, reject) => {
          pollingRef.current = setInterval(async () => {
            attempts++
            try {
              const result = await api.voice.result(job_id)
              if ((result.status === 'completed' || result.status === 'partial') && result.transcript) {
                transcript = result.transcript
                if (pollingRef.current) clearInterval(pollingRef.current)
                resolve()
              } else if (result.status === 'failed') {
                if (pollingRef.current) clearInterval(pollingRef.current)
                reject(new Error('Transcription failed'))
              } else if (attempts >= maxAttempts) {
                if (pollingRef.current) clearInterval(pollingRef.current)
                reject(new Error('Transcription timed out'))
              }
            } catch {
              if (attempts >= maxAttempts) {
                if (pollingRef.current) clearInterval(pollingRef.current)
                reject(new Error('Polling failed'))
              }
            }
          }, 2000)
        })

        // Refresh void status
        const voidData = await api.void.now().catch(() => voidNow)
        if (voidData) setVoidNow(voidData)

        // Request suggestions with transcript context
        const { suggestions: items } = await api.suggestions.request({
          context: transcript,
        })

        const mapped: VoidSuggestion[] = items.slice(0, 3).map(toVoidSuggestion)

        setSuggestions(mapped)
        setOverlaySuggestions(mapped)
        setOverlayTranscript(transcript)
        setOverlayOpen(true)
        setMicPhase('done')
      } catch (err) {
        console.error('[HomePage] voice flow error:', err)
        setMicPhase('idle')
      } finally {
        voice.resetRecording()
      }
    }

    processAudio()

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [voice.state, voice.audioBlob, voice.activeRecorderId])

  // ── Autonomy handlers ──────────────────────────────────────────────────────
  const persistAutonomyLog = useCallback((entries: AutonomyLogEntry[]) => {
    const today = new Date().toDateString()
    const filtered = entries.filter((e) => new Date(e.scheduled_at).toDateString() === today)
    localStorage.setItem('autonomyLog', JSON.stringify(filtered.slice(0, 5)))
  }, [])

  const handleAutonomyRun = useCallback(async () => {
    setAutonomyLoading(true)
    setAutonomyStatus('')
    try {
      const result = await api.autonomy.run()
      if (result.status === 'scheduled') {
        const entry: AutonomyLogEntry = {
          id: Date.now().toString(),
          title: result.suggestion_title ?? result.reason,
          scheduled_at: new Date().toISOString(),
          duration_minutes: result.void_minutes,
          category: deriveCategoryFromTitle(result.suggestion_title ?? ''),
          reason: result.reason,
          block_id: result.block_id,
        }
        const updated = [entry, ...autonomyLog].slice(0, 5)
        setAutonomyLog(updated)
        persistAutonomyLog(updated)
        setAutonomyStatus(`VoidFill scheduled \u201c${entry.title}\u201d`)
        speak(`Done. I've scheduled ${entry.title} for you.`)
        setTimeout(() => setAutonomyStatus(''), 3000)
      } else {
        setAutonomyStatus(result.reason)
        setTimeout(() => setAutonomyStatus(''), 2000)
      }
    } catch {
      setAutonomyStatus('Could not run engine')
      setTimeout(() => setAutonomyStatus(''), 2000)
    } finally {
      setAutonomyLoading(false)
    }
  }, [autonomyLog, persistAutonomyLog, speak])

  const handleUndoAutonomy = useCallback(async (entry: AutonomyLogEntry) => {
    if (entry.block_id) {
      try { await api.schedule.delete(entry.block_id) } catch { /* ignore */ }
    }
    const updated = autonomyLog.filter((e) => e.id !== entry.id)
    setAutonomyLog(updated)
    persistAutonomyLog(updated)
    setAutonomyStatus('Removed from schedule')
    setTimeout(() => setAutonomyStatus(''), 2000)
  }, [autonomyLog, persistAutonomyLog])

  // ── Mic tap handler ───────────────────────────────────────────────────────
  const handleMicTap = useCallback(async () => {
    if (voice.state === 'recording' && voice.activeRecorderId === RECORDER_ID) {
      // Tap 2 → stop
      voice.stopRecording()
    } else {
      // Tap 1 → start recording
      setMicPhase('listening')
      await voice.startRecording(RECORDER_ID)
    }
  }, [voice])

  // ── Overlay handlers (consumed by SuggestionOverlay in Part 3) ────────────
  const handleOverlayClose = useCallback(() => {
    setOverlayOpen(false)
    setMicPhase('idle')
  }, [])

  const handleOverlayAccept = useCallback((accepted: VoidSuggestion) => {
    // Move accepted card to top of home cards with green tint (future)
    setSuggestions((prev) => [accepted, ...prev.filter((s) => s.title !== accepted.title)])
    setOverlayOpen(false)
    setMicPhase('idle')
  }, [])

  const isScheduled = voidNow?.status === 'scheduled'
  const isRecording = voice.state === 'recording' && voice.activeRecorderId === RECORDER_ID
  const micPulsing = isRecording || micPhase === 'processing'

  // Header labels
  const freeLabel = isScheduled
    ? `Right now: ${voidNow!.current_block?.block_type ?? 'Scheduled'}`
    : voidNow?.void_slot
      ? `You have ${formatDuration(voidNow.void_slot.duration_minutes)} free.`
      : 'Finding your free time…'

  const nextLabel = isScheduled
    ? `Check back after this block ends`
    : voidNow?.void_slot
      ? `Free until ${formatTime(voidNow.void_slot.end_time)}`
      : ''

  // Mic hint label
  let micHint: string
  if (isScheduled) micHint = 'No free time right now'
  else if (micPhase === 'listening') micHint = 'Listening… tap to finish'
  else if (micPhase === 'processing') micHint = 'Thinking…'
  else micHint = 'Tap to get a suggestion'

  const userName = localStorage.getItem('userName') ?? 'there'

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <p className={styles.greeting}>
          {getGreeting()}, {userName}
          <PulseIcon />
        </p>
        <h1 className={styles.voidTime}>{freeLabel}</h1>
        {nextLabel ? <p className={styles.nextUp}>{nextLabel}</p> : null}
      </header>

      <section className={styles.micSection}>
        <button
          className={`${styles.micBtn} ${micPulsing ? styles.micBtnPulsing : ''} ${isScheduled ? styles.micBtnDisabled : ''}`}
          onClick={handleMicTap}
          disabled={isScheduled}
          aria-label={micHint}
          style={isScheduled ? { opacity: 0.4, pointerEvents: 'none' } : undefined}
        >
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="9" y="2" width="6" height="11" rx="3" />
            <path d="M5 10a7 7 0 0 0 14 0" />
            <line x1="12" y1="19" x2="12" y2="22" />
            <line x1="9" y1="22" x2="15" y2="22" />
          </svg>
        </button>
        <p className={styles.micHint}>{micHint}</p>

        {autonomyEnabled && !isScheduled && (
          <button
            className={styles.autonomyBtn}
            onClick={handleAutonomyRun}
            disabled={autonomyLoading || micPulsing}
          >
            {autonomyLoading
              ? <><span className={styles.autonomyBtnSpinner} />Thinking...</>
              : 'Let VoidFill decide'}
          </button>
        )}
        {autonomyStatus && (
          <p className={styles.autonomyStatus}>{autonomyStatus}</p>
        )}
      </section>

      {suggestions.length > 0 && (
        <section className={styles.cards}>
          {suggestions.map((s, i) => (
            <SuggestionCard key={s.goal_id ?? i} suggestion={s} />
          ))}
        </section>
      )}

      {micPhase === 'processing' && suggestions.length === 0 && (
        <section className={styles.cards}>
          {[0, 1, 2].map((i) => <div key={i} className={styles.skeleton} />)}
        </section>
      )}

      {/* Autonomy Log ─ surfaced when VoidFill has acted autonomously today */}
      {autonomyLog.length > 0 && (
        <section className={styles.autonomyLogSection}>
          <div className={styles.autonomyLogHeader}>
            <SmallLightningIcon />
            <span className={styles.autonomyLogLabel}>VoidFill acted for you</span>
          </div>
          <div className={styles.autonomyLogList}>
            {autonomyLog.map((entry) => (
              <AutonomyLogRow
                key={entry.id}
                entry={entry}
                onUndo={handleUndoAutonomy}
              />
            ))}
          </div>
        </section>
      )}

      {/* SuggestionOverlay — rendered when overlayOpen is true (Part 3) */}
      {overlayOpen && (
        <SuggestionOverlayLazy
          suggestions={overlaySuggestions}
          transcript={overlayTranscript}
          onClose={handleOverlayClose}
          onAccept={handleOverlayAccept}
        />
      )}
    </div>
  )
}

// ── Lazy overlay import — avoids circular deps, component created in Part 3 ──
// Uses a dynamic import wrapper; falls back gracefully if not yet created.
import { lazy, Suspense } from 'react'
const SuggestionOverlayComponent = lazy(() => import('../components/SuggestionOverlay'))

function SuggestionOverlayLazy(props: {
  suggestions: VoidSuggestion[]
  transcript: string
  onClose: () => void
  onAccept: (s: VoidSuggestion) => void
}) {
  return (
    <Suspense fallback={null}>
      <SuggestionOverlayComponent {...props} />
    </Suspense>
  )
}

// ── Autonomy Log Row ────────────────────────────────────────────────────
function AutonomyLogRow({
  entry,
  onUndo,
}: {
  entry: AutonomyLogEntry
  onUndo: (e: AutonomyLogEntry) => void
}) {
  return (
    <div className={styles.autonomyLogRow}>
      <div className={styles.autonomyLogLeft}>
        <span className={styles.autonomyLogIcon}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="#ED1C24" stroke="none">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
          </svg>
        </span>
        <div>
          <p className={styles.autonomyLogTitle}>{entry.title}</p>
          <p className={styles.autonomyLogMeta}>
            {entry.category} · {entry.duration_minutes} mins
          </p>
        </div>
      </div>
      <div className={styles.autonomyLogRight}>
        <span className={styles.autonomyLogTime}>{formatLogTime(entry.scheduled_at)}</span>
        <button
          className={styles.autonomyLogUndo}
          onClick={() => onUndo(entry)}
        >
          undo
        </button>
      </div>
    </div>
  )
}

function SuggestionCard({ suggestion }: { suggestion: VoidSuggestion }) {
  const color = accentColor(suggestion.title)

  return (
    <div className={styles.card} style={{ '--accent': color } as React.CSSProperties}>
      <div className={styles.cardAccent} />
      <div className={styles.cardIcon}>
        <SuggestionIcon title={suggestion.title} />
      </div>
      <div className={styles.cardBody}>
        <p className={styles.cardTitle}>{suggestion.title}</p>
        <p className={styles.cardMeta}>
          Score {Math.round(suggestion.score * 100)}%
        </p>
      </div>
    </div>
  )
}
