import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../api/client'
import { useVoiceRecorder } from '../hooks/useVoiceRecorder'
import type { ScheduleBlock, VoidNowResponse } from '../types/api'
import styles from './SchedulePage.module.css'

// ── helpers ──────────────────────────────────────────────────────────────
function fmtTime(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true })
  } catch { return iso }
}

function todayLabel() {
  return new Date().toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' })
}

function durationLabel(start: string, end: string) {
  try {
    const mins = Math.round((new Date(end).getTime() - new Date(start).getTime()) / 60_000)
    if (mins < 60) return `${mins} min`
    const h = Math.floor(mins / 60)
    const m = mins % 60
    return m ? `${h}h ${m}m` : `${h}h`
  } catch { return '' }
}

// derive a colour from the block title keywords
const TITLE_COLOR_MAP: Array<[RegExp, string]> = [
  [/class|lecture|lab/i,   '#3B82F6'],
  [/study|assignment|exam/i,'#A855F7'],
  [/work|project|sprint/i, '#ED1C24'],
  [/exercise|gym|walk|run/i,'#10B981'],
  [/free|void|break/i,     '#22c55e'],
  [/personal|errands/i,    '#f59e0b'],
]

function blockColor(title?: string) {
  if (!title) return '#555'
  const match = TITLE_COLOR_MAP.find(([re]) => re.test(title))
  return match ? match[1] : '#888'
}

// ── icons ────────────────────────────────────────────────────────────────
function CalIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  )
}

function MicIcon({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="17" x2="12" y2="22" />
      <line x1="8"  y1="22" x2="16" y2="22" />
    </svg>
  )
}

/** Pick a meaningful time slot based on goal title keywords */
function smartSlot(title: string, idx: number): { hour: number; duration: number } {
  const t = title.toLowerCase()
  if (/study|exam|academic|read|learn|class|lecture|assignment/.test(t))
    return { hour: 9 + idx * 0.5,  duration: 1.5 }
  if (/work|career|api|coding|project|backend|frontend|meeting|job|interview/.test(t))
    return { hour: 10 + idx * 0.5, duration: 2 }
  if (/exercise|workout|gym|run|walk|jog|health|yoga|swim/.test(t))
    return { hour: 18,             duration: 1 }
  if (/water|drink|meditat|personal|habit|skill|growth|guitar|journal/.test(t))
    return { hour: 20,             duration: 0.5 }
  return { hour: 10 + idx * 1.5,  duration: 1 }
}

// ── component ─────────────────────────────────────────────────────────────
export default function SchedulePage() {
  const [blocks, setBlocks]       = useState<ScheduleBlock[]>([])
  const [voidNow, setVoidNow]     = useState<VoidNowResponse | null>(null)
  const [loading, setLoading]     = useState(true)
  const [recording, setRecording] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')

  const { state: recState, start, stop, audioBlob } = useVoiceRecorder()
  const uploadPending = useRef(false)

  // fetch data + auto-sync goals → schedule blocks
  const reload = useCallback(async () => {
    try {
      const [bl, vs, gl] = await Promise.all([api.schedule.list(), api.void.now(), api.goals.list()])
      const fetchedBlocks = bl.blocks ?? []
      const fetchedGoals  = (gl.goals ?? []).slice(0, 6)
      setVoidNow(vs)

      // Auto-create a block for every goal that doesn't have one yet
      const existingTypes = new Set(fetchedBlocks.map(b => b.block_type))
      const todayBase = new Date()
      todayBase.setHours(0, 0, 0, 0)
      let created = 0
      let slotIdx = 0
      for (const goal of fetchedGoals) {
        const key = goal.title.slice(0, 64)
        if (!existingTypes.has(key)) {
          const { hour, duration } = smartSlot(goal.title, slotIdx)
          const s = new Date(todayBase.getTime() + hour * 3_600_000)
          const e = new Date(s.getTime()          + duration * 3_600_000)
          await api.schedule.create({
            start_time: s.toISOString(),
            end_time:   e.toISOString(),
            block_type: key,
          }).catch(() => {})
          existingTypes.add(key)
          created++
        }
        slotIdx++
      }

      if (created > 0) {
        const refreshed = await api.schedule.list()
        setBlocks(refreshed.blocks ?? [])
      } else {
        setBlocks(fetchedBlocks)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { reload() }, [reload])

  // handle voice upload when blob ready
  useEffect(() => {
    if (recState === 'stopped' && audioBlob && uploadPending.current) {
      uploadPending.current = false
      setRecording(false)
      setProcessing(true)
      setStatusMsg('Analysing schedule…')
      ;(async () => {
        try {
          const upload = await api.voice.upload(audioBlob)
          let attempts = 0
          while (attempts < 20) {
            await new Promise(r => setTimeout(r, 1500))
            const result = await api.voice.result(upload.job_id)
            if (result.status === 'completed' || result.status === 'partial') break
            if (result.status === 'failed') throw new Error('Failed')
            attempts++
          }
          // reload() handles auto-syncing goals → blocks
          await reload()
          setStatusMsg('Schedule updated!')
        } catch {
          setStatusMsg('Could not update — try again')
        } finally {
          setProcessing(false)
          setTimeout(() => setStatusMsg(''), 3000)
        }
      })()
    }
  }, [recState, audioBlob, reload])

  const handleMic = useCallback(async () => {
    if (recording) {
      uploadPending.current = true
      stop()
    } else {
      setStatusMsg('Listening…')
      setRecording(true)
      await start()
    }
  }, [recording, start, stop])

  // Sort blocks by start_time, then deduplicate by block_type (keep earliest)
  const sortedBlocks = [...blocks]
    .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())
    .filter((block, _, arr) => arr.findIndex(b => b.block_type === block.block_type) === arr.indexOf(block))

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerRow}>
          <h1 className={styles.title}>Schedule</h1>
          <CalIcon />
        </div>
        <p className={styles.date}>{todayLabel()}</p>
      </div>

      {/* Void slot banner */}
      {voidNow?.void_slot && (
        <div className={styles.voidBanner}>
          <span className={styles.voidDot} />
          <div>
            <p className={styles.voidTitle}>
              {voidNow.void_slot.duration_minutes} min free
            </p>
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className={styles.timeline}>
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className={`${styles.blockSkel} ${styles.shimmer}`} />
          ))
        ) : sortedBlocks.length === 0 ? (
          <div className={styles.empty}>
            <p>No blocks yet — add a goal or record one below</p>
          </div>
        ) : (
          sortedBlocks.map(block => (
            <div
              key={block.id}
              className={styles.block}
              style={{ '--bclr': blockColor(block.block_type) } as React.CSSProperties}
            >
              <div className={styles.blockAccent} />
              <div className={styles.blockBody}>
                <div className={styles.blockTime}>
                  {fmtTime(block.start_time)} — {fmtTime(block.end_time)}
                  <span className={styles.blockDur}>{durationLabel(block.start_time, block.end_time)}</span>
                </div>
                <p className={styles.blockTitle}>{block.block_type}</p>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Status bar + mic FAB */}
      {statusMsg && <p className={styles.status}>{statusMsg}</p>}

      <div className={styles.fabArea}>
        <p className={styles.fabHint}>
          {recording ? 'Tap to stop' : 'Speak to add a block'}
        </p>
        <button
          className={`${styles.fab} ${recording ? styles.fabActive : ''} ${processing ? styles.fabProcessing : ''}`}
          onClick={handleMic}
          disabled={processing}
          aria-label="Record schedule block"
        >
          <MicIcon size={26} />
        </button>
      </div>
    </div>
  )
}

