import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { MemorySummaryResponse } from '../types/api'
import styles from './MemoryPage.module.css'

export default function MemoryPage() {
  const [data, setData] = useState<MemorySummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Record form state
  const [showForm, setShowForm] = useState(false)
  const [formTitle, setFormTitle] = useState('')
  const [formMinutes, setFormMinutes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const loadData = useCallback(() => {
    setLoading(true)
    api.memory
      .summary()
      .then(setData)
      .catch(() => setError('Could not load memory'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const handleRecord = async () => {
    if (!formTitle.trim() || !formMinutes) return
    setSubmitting(true)
    try {
      await api.memory.create({
        title: formTitle.trim(),
        minutes: parseInt(formMinutes, 10),
      })
      setFormTitle('')
      setFormMinutes('')
      setShowForm(false)
      loadData()
    } catch {
      setError('Could not record action')
    } finally {
      setSubmitting(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleRecord()
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Memory</h1>
        <p className={styles.subtitle}>What you've been working on</p>
      </div>

      {loading && (
        <div className={styles.loading}>
          {[0, 1, 2].map((i) => (
            <div key={i} className={styles.skeleton} />
          ))}
        </div>
      )}

      {error && <p className={styles.error}>{error}</p>}

      {data && (
        <>
          {/* Top goals */}
          <section className={styles.section}>
            <p className={styles.sectionLabel}>Top Goals</p>
            {data.top_goals.length === 0 ? (
              <p className={styles.empty}>No activity recorded yet</p>
            ) : (
              <div className={styles.goalList}>
                {data.top_goals.map((g, i) => (
                  <div key={i} className={styles.goalCard}>
                    <div className={styles.goalRow}>
                      <span className={styles.goalTitle}>{g.title}</span>
                      <span className={styles.goalTime}>{g.total_minutes} min</span>
                    </div>
                    <span className={styles.goalSessions}>
                      {g.sessions} session{g.sessions !== 1 ? 's' : ''}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Recent actions */}
          <section className={styles.section}>
            <p className={styles.sectionLabel}>Recent Actions</p>
            {data.recent_actions.length === 0 ? (
              <p className={styles.empty}>Nothing here yet</p>
            ) : (
              <div className={styles.actionList}>
                {data.recent_actions.map((a, i) => (
                  <div key={i} className={styles.actionCard}>
                    <div className={styles.actionRow}>
                      <span className={styles.actionTitle}>{a.title}</span>
                      <span className={styles.actionTime}>{a.minutes} min</span>
                    </div>
                    <span className={styles.actionDate}>
                      {new Date(a.created_at).toLocaleDateString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}

      {/* Record action form */}
      {showForm && (
        <div className={styles.formCard}>
          <p className={styles.formTitle}>Record an Action</p>
          <input
            className={styles.input}
            placeholder="What did you do?"
            value={formTitle}
            onChange={(e) => setFormTitle(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <input
            className={styles.input}
            type="number"
            placeholder="Minutes spent"
            min="1"
            value={formMinutes}
            onChange={(e) => setFormMinutes(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <div className={styles.formActions}>
            <button
              className={styles.cancelBtn}
              onClick={() => setShowForm(false)}
            >
              Cancel
            </button>
            <button
              className={styles.recordBtn}
              onClick={handleRecord}
              disabled={submitting || !formTitle.trim() || !formMinutes}
            >
              {submitting ? 'Saving…' : 'Save'}
            </button>
          </div>
        </div>
      )}

      {/* FAB */}
      <button
        className={styles.fab}
        onClick={() => setShowForm(!showForm)}
        aria-label="Record action"
      >
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#fff"
          strokeWidth="2.5"
          strokeLinecap="round"
        >
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </button>
    </div>
  )
}
