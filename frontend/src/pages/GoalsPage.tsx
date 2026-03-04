import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { Goal } from '../types/api'
import { useVoiceContext } from '../context/VoiceContext'
import styles from './GoalsPage.module.css'

// â”€â”€ Category config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const CATEGORIES = [
  {
    key: 'academic',
    label: 'Academic',
    color: '#ED1C24',
    keywords: ['exam', 'assignment', 'study', 'lecture', 'course', 'class', 'grade', 'academic'],
    Icon: IconBook,
  },
  {
    key: 'career',
    label: 'Career',
    color: '#3B82F6',
    keywords: ['career', 'job', 'resume', 'intern', 'finance', 'p&l', 'trading', 'business', 'salary', 'project', 'deadline', 'meeting', 'client', 'sprint', 'coding', 'backend', 'frontend', 'api', 'deploy'],
    Icon: IconBriefcase,
  },
  {
    key: 'personal',
    label: 'Personal Growth',
    color: '#A855F7',
    keywords: ['guitar', 'habit', 'book', 'read', 'skill', 'learn', 'personal', 'growth', 'language'],
    Icon: IconTrending,
  },
  {
    key: 'health',
    label: 'Health & Rest',
    color: '#10B981',
    keywords: ['sleep', 'walk', 'run', 'exercise', 'gym', 'health', 'rest', 'meditat', 'diet', 'fitness', 'workout', 'jog', 'water', 'stretch', 'yoga'],
    Icon: IconHeart,
  },
] as const

type CategoryKey = (typeof CATEGORIES)[number]['key']

// â”€â”€ Display types (goals + placeholders) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
interface PlaceholderGoal {
  id: string             // starts with 'temp-'
  title: string
  isPlaceholder: true
  isLoading: boolean
  priority: number
  created_at: string
  updated_at: string
  user_id: string
  description: null
  is_active: boolean
}

type DisplayGoal = Goal | PlaceholderGoal

function isPlaceholder(g: DisplayGoal): g is PlaceholderGoal {
  return (g as PlaceholderGoal).isPlaceholder === true
}

// â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function categorizeGoal(goal: Goal): CategoryKey {
  const text = `${goal.title} ${goal.description ?? ''}`.toLowerCase()
  for (const cat of CATEGORIES) {
    if (cat.keywords.some((kw) => text.includes(kw))) return cat.key
  }
  // priority is a 0–1 float; map to a valid integer index
  const idx = Math.floor(goal.priority * CATEGORIES.length) % CATEGORIES.length
  return CATEGORIES[idx >= 0 && idx < CATEGORIES.length ? idx : 0].key
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `Updated ${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `Updated ${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days === 1) return 'Updated yesterday'
  if (days < 7) return `Updated ${days}d ago`
  return 'Updated today'
}

async function pollTranscript(jobId: string, maxAttempts = 20): Promise<string | null> {
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((r) => setTimeout(r, 1500))
    const result = await api.voice.result(jobId)
    if (result.status === 'completed' && result.transcript) return result.transcript
    if (result.status === 'failed') return null
  }
  return null
}

// â”€â”€ Main â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export default function GoalsPage() {
  const voice = useVoiceContext()

  const [goals, setGoals]               = useState<Goal[]>([])
  const [placeholders, setPlaceholders] = useState<PlaceholderGoal[]>([])
  const [loading, setLoading]           = useState(true)
  const [showCacheBanner, setShowCacheBanner] = useState(false)
  const [activeCard, setActiveCard]     = useState<CategoryKey | null>(null)
  const [statusMsg, setStatusMsg]       = useState('')
  const [weeklyFocus, setWeeklyFocus]   = useState<string>(
    () => localStorage.getItem('weeklyFocus') ?? ''
  )

  // â”€â”€ Fetch goals with cache fallback (T17) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const fetchGoals = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true)
    try {
      const { goals: g } = await api.goals.list()
      setGoals(g)
      localStorage.setItem('cachedGoals', JSON.stringify(g))
      setShowCacheBanner(false)
    } catch {
      const cached = localStorage.getItem('cachedGoals')
      if (cached) {
        try {
          setGoals(JSON.parse(cached) as Goal[])
          setShowCacheBanner(true)
        } catch { /* bad JSON, ignore */ }
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchGoals(true)
  }, [fetchGoals])

  // â”€â”€ Dispatch on voice stop (T15, T16, T18) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  useEffect(() => {
    if (voice.state !== 'stopped' || !voice.audioBlob) return

    const recorderId = voice.activeRecorderId
    const blob = voice.audioBlob
    voice.resetRecording()
    setActiveCard(null)

    // â”€â”€ T15: Header mic â€” multi-goal via parseAndCreate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if (recorderId === 'goals-header') {
      setStatusMsg('Processing…')
      ;(async () => {
        try {
          const { job_id } = await api.voice.upload(blob)
          const transcript = await pollTranscript(job_id)
          if (!transcript) throw new Error('No transcript')
          const result = await api.goals.parseAndCreate(transcript)
          await fetchGoals()
          setStatusMsg(`${result.goals.length} goal(s) added!`)
          setTimeout(() => setStatusMsg(''), 2000)
        } catch {
          setStatusMsg('Failed to save. Try again.')
          setTimeout(() => setStatusMsg(''), 2500)
        }
      })()
      return
    }

    // â”€â”€ T18: CTA card â€” weekly focus â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if (recorderId === 'goals-cta') {
      setStatusMsg('Processing…')
      ;(async () => {
        try {
          const { job_id } = await api.voice.upload(blob)
          const transcript = await pollTranscript(job_id)
          if (!transcript) throw new Error('No transcript')

          let focus = transcript
          try {
            const res = await api.goals.weeklyFocus(transcript)
            focus = res.focus
          } catch (err) {
            // 404 = endpoint not yet live â€” fall back to raw transcript (T18)
            const msg = err instanceof Error ? err.message : ''
            if (!msg.includes('404') && !msg.includes('API 4')) throw err
          }
          localStorage.setItem('weeklyFocus', focus)
          setWeeklyFocus(focus)
          setStatusMsg('Weekly focus set!')
          setTimeout(() => setStatusMsg(''), 2000)
        } catch {
          setStatusMsg('Failed to save. Try again.')
          setTimeout(() => setStatusMsg(''), 2500)
        }
      })()
      return
    }

    // â”€â”€ T16: Category card â€” create goal with optimistic placeholder â”€â”€â”€â”€â”€
    const catKey = recorderId as CategoryKey
    if (!CATEGORIES.some((c) => c.key === catKey)) return

    setStatusMsg('Processing…')
    ;(async () => {
      const tempId = `temp-${Date.now()}`
      let transcript: string | null = null

      try {
        const { job_id } = await api.voice.upload(blob)
        transcript = await pollTranscript(job_id)
        if (!transcript) throw new Error('No transcript')

        // Push placeholder immediately after transcript arrives (T16)
        const placeholder: PlaceholderGoal = {
          id: tempId,
          title: transcript.slice(0, 60) + (transcript.length > 60 ? '…' : ''),
          isPlaceholder: true,
          isLoading: true,
          priority: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          user_id: '',
          description: null,
          is_active: true,
        }
        setPlaceholders((prev) => [...prev, placeholder])

        await api.goals.create({ title: transcript.slice(0, 120), priority: 1 })
        // Remove placeholder, refresh real list
        await fetchGoals()
        setPlaceholders((prev) => prev.filter((p) => p.id !== tempId))
        setStatusMsg('Goal added!')
        setTimeout(() => setStatusMsg(''), 2000)
      } catch {
        // Remove placeholder on failure (T16)
        setPlaceholders((prev) => prev.filter((p) => p.id !== tempId))
        setStatusMsg('Failed to save. Try again.')
        setTimeout(() => setStatusMsg(''), 2500)
      }
    })()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [voice.state, voice.activeRecorderId])

  // â”€â”€ Tap handlers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const handleCardTap = async (key: CategoryKey) => {
    if (voice.state === 'recording' && voice.activeRecorderId === key) {
      voice.stopRecording()
      return
    }
    voice.resetRecording()
    setActiveCard(key)
    await voice.startRecording(key)
  }

  const handleCtaTap = async () => {
    if (voice.state === 'recording' && voice.activeRecorderId === 'goals-cta') {
      voice.stopRecording()
      return
    }
    voice.resetRecording()
    await voice.startRecording('goals-cta')
  }

  const handleHeaderMicTap = async () => {
    if (voice.state === 'recording' && voice.activeRecorderId === 'goals-header') {
      voice.stopRecording()
      return
    }
    voice.resetRecording()
    await voice.startRecording('goals-header')
  }

  // â”€â”€ Merge real goals + placeholders into buckets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const buckets = Object.fromEntries(
    CATEGORIES.map((c) => {
      const realGoals = loading ? [] : goals.filter((g) => categorizeGoal(g) === c.key)
      const catPlaceholders = placeholders.filter((p) => {
        // Route placeholder to the active card's category
        return activeCard === c.key || voice.activeRecorderId === c.key
          ? false // while still recording, don't show yet (shown after transcript)
          : p.title.length > 0
            ? CATEGORIES.find((cat) =>
                cat.keywords.some((kw) => p.title.toLowerCase().includes(kw))
              )?.key === c.key
            : false
      })
      return [c.key, [...catPlaceholders, ...realGoals] as DisplayGoal[]]
    })
  ) as Record<CategoryKey, DisplayGoal[]>

  // Include all placeholders in their best-guess bucket
  // (simpler: attach to the category of the recording that produced them)
  const bucketsWithPlaceholders = Object.fromEntries(
    CATEGORIES.map((c) => {
      // Deduplicate by title — keep only the most-recent goal per unique title
      const seenTitles = new Set<string>()
      const realGoals: DisplayGoal[] = loading ? [] : goals
        .filter((g) => categorizeGoal(g) === c.key)
        .filter((g) => {
          const key = g.title.trim().toLowerCase()
          if (seenTitles.has(key)) return false
          seenTitles.add(key)
          return true
        })
      const catPlaceholders: DisplayGoal[] = placeholders.filter((p) => {
        // Loosely match by keywords, fallback to first category
        const matchedCat = CATEGORIES.find((cat) =>
          cat.keywords.some((kw) => p.title.toLowerCase().includes(kw))
        )
        return (matchedCat?.key ?? CATEGORIES[0].key) === c.key
      })
      return [c.key, [...catPlaceholders, ...realGoals]]
    })
  ) as Record<CategoryKey, DisplayGoal[]>

  void buckets // suppress unused warning â€” we use bucketsWithPlaceholders below

  const isVoiceRecording = voice.state === 'recording'

  return (
    <div className={styles.page}>
      {/* â”€â”€ Header â”€â”€ */}
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>Your Goals</h1>
          {/* T15 â€” Header mic button */}
          <button
            className={`${styles.headerMic} ${isVoiceRecording && voice.activeRecorderId === 'goals-header' ? styles.headerMicActive : ''}`}
            onClick={() => void handleHeaderMicTap()}
            aria-label={isVoiceRecording && voice.activeRecorderId === 'goals-header' ? 'Stop recording' : 'Add goals by voice'}
          >
            <MicSVG size={16} color="#fff" />
          </button>
        </div>
        <p className={styles.subtitle}>Tap any card and speak to update</p>
        {statusMsg && <p className={styles.statusMsg}>{statusMsg}</p>}
        {voice.error && <p className={styles.errorMsg}>{voice.error}</p>}
      </header>

      {/* T17 â€” Cache banner */}
      {showCacheBanner && (
        <button
          className={styles.cacheBanner}
          onClick={() => void fetchGoals()}
        >
          Showing cached goals — tap to retry
        </button>
      )}

      {/* â”€â”€ 2Ã—2 Grid â”€â”€ */}
      <section className={styles.grid}>
        {CATEGORIES.map((cat) => {
          const catGoals = bucketsWithPlaceholders[cat.key]
          const isActive = activeCard === cat.key && isVoiceRecording

          return (
            <GoalCard
              key={cat.key}
              category={cat}
              goals={catGoals}
              loading={loading}
              active={isActive}
              onTap={() => void handleCardTap(cat.key)}
            />
          )
        })}
      </section>

      {/* â”€â”€ Weekly Focus CTA â”€â”€ */}
      <button
        className={`${styles.ctaCard} ${isVoiceRecording && voice.activeRecorderId === 'goals-cta' ? styles.ctaCardActive : ''}`}
        onClick={() => void handleCtaTap()}
      >
        <div className={`${styles.ctaMicCircle} ${isVoiceRecording && voice.activeRecorderId === 'goals-cta' ? styles.ctaMicCircleActive : ''}`}>
          <MicSVG size={18} color="#fff" />
        </div>
        <div className={styles.ctaText}>
          <p className={styles.ctaTitle}>
            {isVoiceRecording && voice.activeRecorderId === 'goals-cta'
              ? 'Listening…'
              : weeklyFocus
              ? weeklyFocus
              : "What's your focus this week?"}
          </p>
          <p className={styles.ctaSub}>
            {weeklyFocus ? 'Tap to update' : 'Speak to set a weekly priority'}
          </p>
        </div>
      </button>
    </div>
  )
}

// â”€â”€ Goal Card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
type CatConfig = (typeof CATEGORIES)[number]

function GoalCard({
  category,
  goals,
  loading,
  active,
  onTap,
}: {
  category: CatConfig
  goals: DisplayGoal[]
  loading: boolean
  active: boolean
  onTap: () => void
}) {
  const { color, label, Icon } = category
  const latest = goals.slice(0, 3)
  const realGoals = goals.filter((g): g is Goal => !isPlaceholder(g))
  const goalsWithDates = realGoals.filter((g) => g.updated_at || g.created_at)
  const lastUpdated = goalsWithDates.length > 0
    ? goalsWithDates.reduce((a, b) => (a.updated_at ?? a.created_at) > (b.updated_at ?? b.created_at) ? a : b).updated_at ?? goalsWithDates[0].created_at
    : null

  return (
    <button
      className={`${styles.card} ${active ? styles.cardActive : ''}`}
      style={{ '--cat-color': color } as React.CSSProperties}
      onClick={onTap}
      aria-label={`${label} goals — tap to update by voice`}
    >
      {/* Colored top border */}
      <div className={styles.cardTopBar} />

      {/* Icon */}
      <div className={styles.iconCircle}>
        <Icon color={color} />
      </div>

      {/* Title */}
      <p className={styles.cardTitle}>{label}</p>

      {/* Goal items */}
      <div className={styles.cardGoals}>
        {loading && (
          <>
            <div className={styles.goalSkeleton} />
            <div className={styles.goalSkeleton} style={{ width: '70%' }} />
          </>
        )}
        {!loading && latest.length === 0 && (
          <p className={styles.emptyHint}>Tap to add goals</p>
        )}
        {!loading && latest.map((g) => (
          isPlaceholder(g) ? (
            /* T16 â€” placeholder with spinner dot */
            <span key={g.id} className={styles.goalItemPlaceholder}>
              <span className={styles.spinnerDot} />
              {g.title}
            </span>
          ) : (
            <p key={g.id} className={styles.goalItem}>{g.title}</p>
          )
        ))}
      </div>

      {/* Timestamp */}
      {lastUpdated && (
        <p className={styles.timestamp}>{timeAgo(lastUpdated)}</p>
      )}

      {active && (
        <div className={styles.listeningBadge}>🎙 Listening…</div>
      )}
    </button>
  )
}

// â”€â”€ SVG Icons â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function MicSVG({ size, color }: { size: number; color: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="2" width="6" height="11" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="19" x2="12" y2="22" />
      <line x1="9" y1="22" x2="15" y2="22" />
    </svg>
  )
}

function IconBook({ color }: { color: string }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  )
}

function IconBriefcase({ color }: { color: string }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </svg>
  )
}

function IconTrending({ color }: { color: string }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
      <polyline points="17 6 23 6 23 12" />
    </svg>
  )
}

function IconHeart({ color }: { color: string }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  )
}

