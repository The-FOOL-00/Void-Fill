import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useVoiceRecorder } from '../hooks/useVoiceRecorder'
import { api } from '../api/client'
import styles from './OnboardingPage.module.css'

// ── Step definitions ──────────────────────────────────────────────────────────
const STEPS = [
  {
    id: 1,
    phase: 'Your Routine',
    heading: 'Tell me about your\ntypical day.',
    subtitle: "Speak naturally. I'll figure out the rest.",
  },
  {
    id: 2,
    phase: 'Your Goals',
    heading: "What are you\ntrying to achieve?",
    subtitle: "Tell me what matters most to you right now.",
  },
  {
    id: 3,
    phase: 'Your Focus',
    heading: "When do you\ndo your best work?",
    subtitle: "Morning, night — whenever. No wrong answer.",
  },
]

// ── Poll helper ───────────────────────────────────────────────────────────────
async function pollTranscript(jobId: string, maxAttempts = 20): Promise<string | null> {
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((r) => setTimeout(r, 1500))
    const result = await api.voice.result(jobId)
    if (result.status === 'completed' && result.transcript) return result.transcript
    if (result.status === 'failed') return null
  }
  return null
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function OnboardingPage() {
  const navigate = useNavigate()
  const [stepIndex, setStepIndex] = useState(0)
  const [transcripts, setTranscripts] = useState<string[]>(['', '', ''])
  const [liveText, setLiveText] = useState('')
  const [isPolling, setIsPolling] = useState(false)

  const { state: recState, start, stop, audioBlob, error, reset } = useVoiceRecorder()
  const [hasRecorded, setHasRecorded] = useState(false)
  const step = STEPS[stepIndex]
  const isRecording = recState === 'recording'
  const drawerOpen = isRecording || recState === 'stopped' || isPolling || liveText.length > 0

  // ── After recording stops, upload + poll ─────────────────────────────────
  useEffect(() => {
    if (recState !== 'stopped' || !audioBlob) return

    let cancelled = false
    setIsPolling(true)

    ;(async () => {
      try {
        const { job_id } = await api.voice.upload(audioBlob)
        const transcript = await pollTranscript(job_id)
        if (!cancelled) {
          if (transcript) {
            const next = [...transcripts]
            next[stepIndex] = transcript
            setTranscripts(next)
            setLiveText(transcript)
          } else {
            setLiveText('Got it — tap Next to continue')
          }
        }
      } catch {
        if (!cancelled) setLiveText('Got it — tap Next to continue')
      } finally {
        if (!cancelled) {
          setIsPolling(false)
          setHasRecorded(true)
        }
      }
    })()

    return () => { cancelled = true }
  }, [recState, audioBlob]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Simulate live typing effect while recording ──────────────────────────
  const liveDotsRef = useRef('')
  useEffect(() => {
    if (!isRecording) return
    setLiveText('')
    let count = 0
    const timer = setInterval(() => {
      count = (count + 1) % 4
      liveDotsRef.current = '●'.repeat(count + 1)
      setLiveText(liveDotsRef.current)
    }, 400)
    return () => clearInterval(timer)
  }, [isRecording])

  // ── Handlers ────────────────────────────────────────────────────────────
  const handleMicPress = async () => {
    if (isRecording) {
      stop()
    } else {
      reset()
      setLiveText('')
      await start()
    }
  }

  const handleNext = () => {
    if (stepIndex < STEPS.length - 1) {
      setStepIndex((i) => i + 1)
      setLiveText('')
      setHasRecorded(false)
      reset()
    } else {
      // Onboarding complete → go to home
      localStorage.setItem('onboardingComplete', 'true')
      navigate('/home')
    }
  }

  const canAdvance = hasRecorded && !isPolling && !isRecording

  return (
    <div className={styles.page}>
      {/* ── Skip button ── */}
      <button className={styles.skipBtn} onClick={() => {
        localStorage.setItem('onboardingComplete', 'true')
        navigate('/home')
      }}>
        Skip
      </button>

      {/* ── Top Progress Bar ── */}
      <div className={styles.progressRow}>
        {STEPS.map((s, i) => (
          <div
            key={s.id}
            className={`${styles.progressDot} ${
              i === stepIndex
                ? styles.progressDotActive
                : i < stepIndex
                ? styles.progressDotDone
                : styles.progressDotFuture
            }`}
          />
        ))}
      </div>

      {/* ── Step Label ── */}
      <p className={styles.stepLabel}>
        Step {step.id} of {STEPS.length} — {step.phase}
      </p>

      {/* ── Heading ── */}
      <h1 className={styles.heading}>
        {step.heading.split('\n').map((line, i) => (
          <span key={i}>
            {line}
            {i < step.heading.split('\n').length - 1 && <br />}
          </span>
        ))}
      </h1>

      {/* ── Mic Button ── */}
      <div className={styles.micArea}>
        <button
          className={`${styles.micRing} ${isRecording ? styles.micRingRecording : ''}`}
          onClick={handleMicPress}
          aria-label={isRecording ? 'Stop recording' : 'Start recording'}
        >
          <div className={styles.micCircle}>
            {isPolling ? (
              <LoadingSpinner />
            ) : (
              <MicIcon recording={isRecording} />
            )}
          </div>
        </button>
      </div>

      {/* ── Subtitle ── */}
      <p className={styles.subtitle}>{step.subtitle}</p>

      {error && <p className={styles.errorText}>{error}</p>}

      {/* ── Next Button (once recorded) ── */}
      {canAdvance && (
        <button className={styles.nextBtn} onClick={handleNext}>
          {stepIndex < STEPS.length - 1 ? 'Next →' : 'Get Started'}
        </button>
      )}

      {/* ── Listening Drawer ── */}
      <div className={`${styles.drawer} ${drawerOpen ? styles.drawerOpen : ''}`}>
        <p className={styles.drawerLabel}>
          {isPolling ? 'PROCESSING…' : isRecording ? 'LISTENING' : 'CAPTURED'}
        </p>
        <p className={styles.drawerText}>{liveText || '…'}</p>
      </div>

      {/* ── Step Pagination Dots ── */}
      <div className={styles.paginationDots}>
        {STEPS.map((_, i) => (
          <span
            key={i}
            className={`${styles.dot} ${i === stepIndex ? styles.dotActive : ''}`}
          />
        ))}
      </div>
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────
function MicIcon({ recording }: { recording: boolean }) {
  return (
    <svg
      width="44"
      height="44"
      viewBox="0 0 24 24"
      fill="none"
      stroke={recording ? '#ED1C24' : '#111111'}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="9" y="2" width="6" height="11" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="19" x2="12" y2="22" />
      <line x1="9" y1="22" x2="15" y2="22" />
    </svg>
  )
}

function LoadingSpinner() {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 24 24"
      fill="none"
      stroke="#888"
      strokeWidth="2.5"
      strokeLinecap="round"
    >
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83">
        <animateTransform
          attributeName="transform"
          type="rotate"
          from="0 12 12"
          to="360 12 12"
          dur="1s"
          repeatCount="indefinite"
        />
      </path>
    </svg>
  )
}
