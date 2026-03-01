import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../api/client'
import { useVoiceRecorder } from '../hooks/useVoiceRecorder'
import type { Note } from '../types/api'
import styles from './NotesPage.module.css'

// ── helpers ───────────────────────────────────────────────────────────────
function relativeTime(iso: string) {
  try {
    const diff = Date.now() - new Date(iso).getTime()
    const mins = Math.floor(diff / 60_000)
    if (mins < 1)   return 'Just now'
    if (mins < 60)  return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs  < 24)  return `${hrs}h ago`
    const days = Math.floor(hrs / 24)
    return `${days}d ago`
  } catch { return '' }
}

function excerpt(text: string, max = 100) {
  if (!text) return ''
  return text.length > max ? `${text.slice(0, max)}…` : text
}

// ── icons ──────────────────────────────────────────────────────────────────
function NoteIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <line x1="10" y1="9"  x2="8" y2="9" />
    </svg>
  )
}

function MicIcon({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="17" x2="12" y2="22" />
      <line x1="8"  y1="22" x2="16" y2="22" />
    </svg>
  )
}

// ── component ─────────────────────────────────────────────────────────────
export default function NotesPage() {
  const [notes, setNotes]         = useState<Note[]>([])
  const [loading, setLoading]     = useState(true)
  const [recording, setRecording] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')
  const [expanded, setExpanded]   = useState<string | null>(null)

  const { state: recState, start, stop, audioBlob } = useVoiceRecorder()
  const uploadPending = useRef(false)

  const reload = useCallback(async () => {
    try {
      const res = await api.notes.list()
      setNotes(res.notes ?? [])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { reload() }, [reload])

  // Upload when blob is ready after stop
  useEffect(() => {
    if (recState === 'stopped' && audioBlob && uploadPending.current) {
      uploadPending.current = false
      setRecording(false)
      setProcessing(true)
      setStatusMsg('Saving note…')
      ;(async () => {
        try {
          const upload = await api.voice.upload(audioBlob)
          let attempts = 0
          while (attempts < 20) {
            await new Promise(r => setTimeout(r, 1500))
            const result = await api.voice.result(upload.job_id)
            if (result.status === 'completed') break
            if (result.status === 'failed') throw new Error('Failed')
            attempts++
          }
          await reload()
          setStatusMsg('Note saved!')
        } catch {
          setStatusMsg('Could not save — try again')
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

  // Sort newest first
  const sortedNotes = [...notes].sort((a, b) =>
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerRow}>
          <h1 className={styles.title}>Notes</h1>
          <NoteIcon />
        </div>
        <p className={styles.subtitle}>Your voice-captured thoughts</p>
      </div>

      {/* Notes list */}
      <div className={styles.list}>
        {loading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className={`${styles.noteSkel} ${styles.shimmer}`} />
          ))
        ) : sortedNotes.length === 0 ? (
          <div className={styles.empty}>
            <p>No notes yet</p>
            <p className={styles.emptyHint}>Tap the mic below to capture a thought</p>
          </div>
        ) : (
          sortedNotes.map(note => {
            const isOpen = expanded === note.id
            return (
              <button
                key={note.id}
                className={`${styles.noteCard} ${isOpen ? styles.noteCardOpen : ''}`}
                onClick={() => setExpanded(isOpen ? null : note.id)}
              >
                <div className={styles.noteTop}>
                  <div className={styles.noteAccentBar} />
                  <div className={styles.noteContent}>
                    <p className={styles.noteText}>
                      {isOpen ? (note.text || '') : excerpt(note.text || '')}
                    </p>
                    <span className={styles.noteTime}>{relativeTime(note.created_at)}</span>
                  </div>
                </div>

              </button>
            )
          })
        )}
      </div>

      {/* Status */}
      {statusMsg && <p className={styles.status}>{statusMsg}</p>}

      {/* Mic FAB */}
      <div className={styles.fabArea}>
        <p className={styles.fabHint}>
          {recording ? 'Tap to stop recording' : 'New voice note'}
        </p>
        <button
          className={`${styles.fab} ${recording ? styles.fabActive : ''} ${processing ? styles.fabProcessing : ''}`}
          onClick={handleMic}
          disabled={processing}
          aria-label="Record note"
        >
          <MicIcon size={26} />
        </button>
      </div>
    </div>
  )
}

