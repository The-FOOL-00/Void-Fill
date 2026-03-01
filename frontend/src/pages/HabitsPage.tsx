import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { HabitSummaryResponse } from '../types/api'
import styles from './HabitsPage.module.css'

export default function HabitsPage() {
  const [data, setData] = useState<HabitSummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.habits
      .summary()
      .then(setData)
      .catch(() => setError('Could not load habits'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Habits</h1>
        <p className={styles.subtitle}>Your consistency patterns</p>
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
          {/* Average session */}
          <section className={styles.section}>
            <div className={styles.statCard}>
              <p className={styles.statLabel}>Avg Session</p>
              <p className={styles.statValue}>{data.avg_session_minutes} min</p>
            </div>
          </section>

          {/* Top habits */}
          <section className={styles.section}>
            <p className={styles.sectionLabel}>Top Habits</p>
            {data.top_habits.length === 0 ? (
              <p className={styles.empty}>No habits tracked yet</p>
            ) : (
              <div className={styles.habitList}>
                {data.top_habits.map((h, i) => (
                  <div key={i} className={styles.habitCard}>
                    <div className={styles.habitHeader}>
                      <span className={styles.habitTitle}>{h.goal_title}</span>
                      <span className={styles.habitStrength}>
                        {Math.round(h.habit_strength * 100)}%
                      </span>
                    </div>
                    <div className={styles.habitBar}>
                      <div
                        className={styles.habitBarFill}
                        style={{ width: `${Math.round(h.habit_strength * 100)}%` }}
                      />
                    </div>
                    <div className={styles.habitMeta}>
                      <span>{h.sessions} sessions</span>
                      <span>{h.total_minutes} min total</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Time patterns */}
          <section className={styles.section}>
            <p className={styles.sectionLabel}>Active Hours</p>
            {data.time_patterns.length === 0 ? (
              <p className={styles.empty}>Not enough data yet</p>
            ) : (
              <div className={styles.patternGrid}>
                {data.time_patterns.map((tp) => (
                  <div key={tp.hour} className={styles.patternCell}>
                    <div
                      className={styles.patternBar}
                      style={{
                        height: `${Math.min(100, tp.sessions * 20)}%`,
                      }}
                    />
                    <span className={styles.patternLabel}>
                      {tp.hour % 12 === 0 ? 12 : tp.hour % 12}{tp.hour < 12 ? 'a' : 'p'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
