/**
 * ReflectionPage — Weekly Reflection screen
 *
 * Fetches GET /reflection/latest and renders:
 *  - Empty state if 404 / no data
 *  - Full reflection view with audio playback, real stats, priority card,
 *    and "Update Goals for Next Week" voice recording flow
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { ReflectionResponse } from '../types/api'
import { useVoiceContext } from '../context/VoiceContext'
import { useSpeechOutput } from '../hooks/useSpeechOutput'
import styles from './ReflectionPage.module.css'

// ── Waveform bar count ────────────────────────────────────────────────────────
const BAR_COUNT = 18

// ── Date range formatting ─────────────────────────────────────────────────────
function formatDateRange(start: string, end: string): string {
  const fmt = (d: string) =>
    new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  return `${fmt(start)} — ${fmt(end)}`
}

// ── Category accent colours (fallback if stat.category is unknown) ──────────
const CAT_COLORS: Record<string, string> = {
  academic: '#ED1C24',
  career:   '#3B82F6',
  personal: '#A855F7',
  health:   '#10B981',
}
function categoryColor(cat: string): string {
  return CAT_COLORS[cat.toLowerCase()] ?? '#888888'
}

// ── Poll helper ───────────────────────────────────────────────────────────────
async function pollTranscript(jobId: string, max = 20, interval = 1500): Promise<string | null> {
  for (let i = 0; i < max; i++) {
    await new Promise((r) => setTimeout(r, interval))
    const res = await api.voice.result(jobId)
    if ((res.status === 'completed' || res.status === 'partial') && res.transcript) return res.transcript
    if (res.status === 'failed') return null
  }
  return null
}

// ── Main component ────────────────────────────────────────────────────────────
export default function ReflectionPage() {
  const navigate = useNavigate()
  const voice    = useVoiceContext()
  const { speak, cancel, isSpeaking } = useSpeechOutput()

  // API state
  const [loading, setLoading]     = useState(true)
  const [isEmpty, setIsEmpty]     = useState(false)
  const [data, setData]           = useState<ReflectionResponse | null>(null)

  // Playback state
  const [isPlaying, setIsPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // Update Goals recording state
  type UpdatePhase = 'idle' | 'listening' | 'processing' | 'done' | 'error'
  const [updatePhase, setUpdatePhase] = useState<UpdatePhase>('idle')

  // ── Fetch reflection on mount ──────────────────────────────────────────────
  useEffect(() => {
    api.reflection.latest()
      .then((res) => {
        // Treat completely empty stats as "no data yet"
        if (!res || res.stats.length === 0) {
          setIsEmpty(true)
        } else {
          setData(res)
        }
      })
      .catch((err: unknown) => {
        // 404 or any error → empty state
        const msg = err instanceof Error ? err.message : ''
        if (msg.includes('404') || msg.includes('API 4')) {
          setIsEmpty(true)
        } else {
          setIsEmpty(true) // graceful degradation
        }
      })
      .finally(() => setLoading(false))
  }, [])

  // ── Audio setup when data arrives ─────────────────────────────────────────
  useEffect(() => {
    if (!data?.audio_url) return
    const audio = new Audio(data.audio_url)
    audio.addEventListener('ended', () => setIsPlaying(false))
    audioRef.current = audio
    return () => {
      audio.pause()
      audioRef.current = null
    }
  }, [data?.audio_url])

  // ── Play / Pause handler ───────────────────────────────────────────────────
  const handlePlayPause = useCallback(() => {
    if (!data) return

    if (data.audio_url && audioRef.current) {
      // HTML Audio playback
      if (isPlaying) {
        audioRef.current.pause()
        setIsPlaying(false)
      } else {
        void audioRef.current.play()
        setIsPlaying(true)
      }
    } else if (data.summary_text) {
      // SpeechSynthesis fallback
      if (isSpeaking) {
        cancel()
        setIsPlaying(false)
      } else {
        speak(data.summary_text)
        setIsPlaying(true)
      }
    }
  }, [data, isPlaying, isSpeaking, speak, cancel])

  // Sync isPlaying with SpeechSynthesis isSpeaking (for fallback path)
  useEffect(() => {
    if (!data?.audio_url) {
      setIsPlaying(isSpeaking)
    }
  }, [isSpeaking, data?.audio_url])

  // Cleanup audio on unmount
  useEffect(() => () => {
    audioRef.current?.pause()
    cancel()
  }, [cancel])

  // ── "Update Goals for Next Week" — react to voice stopped ─────────────────
  useEffect(() => {
    if (
      voice.state !== 'stopped' ||
      voice.activeRecorderId !== 'reflection-goals' ||
      !voice.audioBlob
    ) return

    const blob = voice.audioBlob
    voice.resetRecording()
    setUpdatePhase('processing')

    ;(async () => {
      try {
        const { job_id } = await api.voice.upload(blob)
        const transcript = await pollTranscript(job_id)
        if (!transcript) throw new Error('No transcript')

        await api.goals.parseAndCreate(transcript)
        setUpdatePhase('done')
        speak("Got it. I'll use these for next week's suggestions.")
        setTimeout(() => setUpdatePhase('idle'), 2000)
      } catch {
        setUpdatePhase('error')
        setTimeout(() => setUpdatePhase('idle'), 2500)
      }
    })()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [voice.state, voice.activeRecorderId])

  // ── Handle update-goals button tap ────────────────────────────────────────
  const handleUpdateGoals = () => {
    if (updatePhase === 'processing') return
    if (updatePhase === 'listening' || voice.state === 'recording') {
      voice.stopRecording()
      return
    }
    setUpdatePhase('listening')
    void voice.startRecording('reflection-goals')
  }

  const updateBtnLabel = () => {
    if (updatePhase === 'listening')  return 'Listening… tap to finish'
    if (updatePhase === 'processing') return 'Processing…'
    if (updatePhase === 'done')       return 'Goals updated! ✓'
    if (updatePhase === 'error')      return 'Something went wrong'
    return 'Update Goals for Next Week'
  }

  // ── Loading skeleton ───────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.skeleton} style={{ height: 40, width: '60%', marginBottom: 8 }} />
        <div className={styles.skeleton} style={{ height: 20, width: '40%', marginBottom: 24 }} />
        <div className={styles.skeleton} style={{ height: 160, borderRadius: 20, marginBottom: 14 }} />
        <div className={styles.skeleton} style={{ height: 140, borderRadius: 12, marginBottom: 14 }} />
        <div className={styles.skeleton} style={{ height: 88, borderRadius: 16 }} />
      </div>
    )
  }

  // ── Empty state ────────────────────────────────────────────────────────────
  if (isEmpty || !data) {
    return (
      <div className={styles.page}>
        <header className={styles.header}>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>Weekly Reflection</h1>
            <CalendarIcon />
          </div>
        </header>
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>
            <CalendarIconLarge />
          </div>
          <p className={styles.emptyTitle}>
            Your first reflection will be ready after your first week of use.
          </p>
          <p className={styles.emptySubtext}>
            In the meantime, set your goals and start using VoidFill.
          </p>
          <button className={styles.emptyBtn} onClick={() => navigate('/goals')}>
            Go to Goals
          </button>
        </div>
      </div>
    )
  }

  // ── Active state ───────────────────────────────────────────────────────────
  return (
    <div className={styles.page}>

      {/* Header */}
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>Weekly Reflection</h1>
          <CalendarIcon />
        </div>
        <p className={styles.dateLabel}>{formatDateRange(data.week_start, data.week_end)}</p>
      </header>

      {/* Audio summary card */}
      <section className={styles.reviewCard}>
        <p className={styles.reviewLabel}>THIS WEEK IN REVIEW</p>

        <div className={`${styles.waveform} ${isPlaying ? styles.waveformPlaying : ''}`}>
          {Array.from({ length: BAR_COUNT }, (_, i) => (
            <div
              key={i}
              className={styles.bar}
              style={{ '--bar-delay': `${(i * 0.065).toFixed(3)}s` } as React.CSSProperties}
            />
          ))}
        </div>

        <button
          className={`${styles.playBtn} ${isPlaying ? styles.playBtnActive : ''}`}
          onClick={handlePlayPause}
          aria-label={isPlaying ? 'Pause summary' : 'Play summary'}
        >
          {isPlaying ? <PauseIcon /> : <PlayIcon />}
        </button>

        <p className={styles.summaryLabel}>
          {isPlaying ? 'Playing…' : '2 min summary ready'}
        </p>
      </section>

      {/* Stats rows */}
      <section className={styles.statsCard}>
        {data.stats.map((stat, i) => (
          <div
            key={stat.category}
            className={`${styles.statRow} ${i < data.stats.length - 1 ? styles.statRowBorder : ''}`}
          >
            <span
              className={styles.statDot}
              style={{ background: categoryColor(stat.category) }}
            />
            <span className={styles.statName}>{stat.category}</span>
            <span className={`${styles.statValue} ${stat.neglected ? styles.statValueNeglected : ''}`}>
              {stat.sessions === 0
                ? '0 sessions'
                : `${stat.sessions} session${stat.sessions !== 1 ? 's' : ''} · ${stat.hours} hrs`}
            </span>
          </div>
        ))}
      </section>

      {/* Priority callout */}
      {data.priority_next_week && (
        <section className={styles.insightCard}>
          <div className={styles.insightIcon}>
            <LightningIcon />
          </div>
          <div className={styles.insightBody}>
            <p className={styles.insightTitle}>Priority next week</p>
            <p className={styles.insightText}>{data.priority_next_week}</p>
          </div>
        </section>
      )}

      {/* Update Goals button */}
      <div className={styles.updateGoalsWrapper}>
        <button
          className={`${styles.updateGoalsBtn} ${updatePhase === 'listening' ? styles.updateGoalsBtnListening : ''}`}
          onClick={handleUpdateGoals}
          disabled={updatePhase === 'processing'}
        >
          {updateBtnLabel()}
        </button>
        <p className={styles.updateGoalsHint}>
          {updatePhase === 'idle' ? 'Tap to speak your updates' : ''}
        </p>
      </div>

    </div>
  )
}

// ── SVG Icons ──────────────────────────────────────────────────────────────────
function CalendarIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#888" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  )
}

function CalendarIconLarge() {
  return (
    <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="#444" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  )
}

function PlayIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="#ffffff" stroke="none">
      <polygon points="5,3 19,12 5,21" />
    </svg>
  )
}

function PauseIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="#ffffff" stroke="none">
      <rect x="6" y="4" width="4" height="16" rx="1" />
      <rect x="14" y="4" width="4" height="16" rx="1" />
    </svg>
  )
}

function LightningIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="#ED1C24" stroke="none">
      <polygon points="13,2 3,14 12,14 11,22 21,10 12,10" />
    </svg>
  )
}
