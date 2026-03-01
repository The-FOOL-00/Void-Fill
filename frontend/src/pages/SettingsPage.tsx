import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import styles from './SettingsPage.module.css'

const CATEGORIES = [
  { label: 'Academic',        color: '#ED1C24', icon: '📚' },
  { label: 'Career',          color: '#3B82F6', icon: '💼' },
  { label: 'Personal Growth', color: '#A855F7', icon: '📈' },
  { label: 'Health & Rest',   color: '#10B981', icon: '💚' },
]

const RESET_KEYS = [
  'onboardingComplete',
  'userName',
  'routineTranscript',
  'goalsTranscript',
  'initialGoals',
  'scheduleSkeleton',
  'weeklyFocus',
  'lastSuggestion',
  'cachedGoals',
  'authToken',
]

function ChevronIcon({ rotated }: { rotated?: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`${styles.chevron} ${rotated ? styles.chevronRotated : ''}`}
    >
      <polyline points="9 18 15 12 9 6" />
    </svg>
  )
}

function EditIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  )
}

export default function SettingsPage() {
  const navigate = useNavigate()

  const [userName, setUserName]         = useState(
    () => localStorage.getItem('userName') ?? 'Student'
  )
  const [editingName, setEditingName]   = useState(false)
  const [nameInput, setNameInput]       = useState(userName)
  const [showResetModal, setShowResetModal] = useState(false)
  const [aboutOpen, setAboutOpen]       = useState(false)
  const [autonomyEnabled, setAutonomyEnabled] = useState(
    () => localStorage.getItem('autonomyEnabled') !== 'false'
  )

  const handleAutonomyToggle = () => {
    const next = !autonomyEnabled
    setAutonomyEnabled(next)
    localStorage.setItem('autonomyEnabled', String(next))
  }

  const nameInputRef = useRef<HTMLInputElement>(null)

  // Autofocus input when edit mode opens
  useEffect(() => {
    if (editingName) nameInputRef.current?.focus()
  }, [editingName])

  const handleNameEdit = () => {
    setNameInput(userName)
    setEditingName(true)
  }

  const handleNameDone = () => {
    const trimmed = nameInput.trim() || 'Student'
    localStorage.setItem('userName', trimmed)
    setUserName(trimmed)
    setEditingName(false)
  }

  const handleNameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleNameDone()
    if (e.key === 'Escape') setEditingName(false)
  }

  const handleReset = () => {
    RESET_KEYS.forEach((k) => localStorage.removeItem(k))
    navigate('/onboarding')
  }

  const avatarLetter = (userName.trim()[0] ?? 'S').toUpperCase()

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <h1 className={styles.title}>Settings</h1>
        <p className={styles.subtitle}>Preferences &amp; app info</p>
      </div>

      {/* Profile section */}
      <section className={styles.section}>
        <p className={styles.sectionLabel}>Profile</p>
        <div className={styles.card}>
          <div className={styles.profileRow}>
            <div className={styles.avatar}>{avatarLetter}</div>
            <div className={styles.profileInfo}>
              <p className={styles.profileName}>{userName}</p>
              <p className={styles.profileSub}>Demo account</p>
            </div>
          </div>
        </div>
      </section>

      {/* Account section — T24 + T25 */}
      <section className={styles.section}>
        <p className={styles.sectionLabel}>Account</p>
        <div className={styles.card}>

          {/* T24 — Editable name row */}
          <div
            className={`${styles.row} ${styles.rowDivider} ${styles.rowTappable}`}
            onClick={editingName ? undefined : handleNameEdit}
            role={editingName ? undefined : 'button'}
            tabIndex={editingName ? undefined : 0}
            onKeyDown={(e) => !editingName && e.key === 'Enter' && handleNameEdit()}
            aria-label="Edit your name"
          >
            <span className={styles.rowLabel}>Your Name</span>
            {editingName ? (
              <div className={styles.nameEditWrapper}>
                <input
                  ref={nameInputRef}
                  className={styles.nameInput}
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  onKeyDown={handleNameKeyDown}
                  maxLength={40}
                  aria-label="Your name"
                />
                <button
                  className={styles.nameDoneBtn}
                  onClick={(e) => { e.stopPropagation(); handleNameDone() }}
                >
                  Done
                </button>
              </div>
            ) : (
              <div className={styles.rowValueWithIcon}>
                <span className={styles.rowValue}>{userName}</span>
                <span className={styles.editIcon}><EditIcon /></span>
              </div>
            )}
          </div>

          {/* T25 — Reset Onboarding */}
          <div
            className={`${styles.row} ${styles.rowTappable}`}
            onClick={() => setShowResetModal(true)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && setShowResetModal(true)}
          >
            <span className={styles.rowRed}>Reset Onboarding</span>
          </div>
        </div>
      </section>

      {/* Goal categories */}
      <section className={styles.section}>
        <p className={styles.sectionLabel}>Goal Categories</p>
        <div className={styles.card}>
          {CATEGORIES.map((cat, i) => (
            <div
              key={cat.label}
              className={`${styles.catRow} ${i < CATEGORIES.length - 1 ? styles.catRowDivider : ''}`}
            >
              <span className={styles.catDot} style={{ background: cat.color }} />
              <span className={styles.catIcon}>{cat.icon}</span>
              <span className={styles.catLabel}>{cat.label}</span>
              <span className={styles.catColor}>{cat.color}</span>
            </div>
          ))}
        </div>
      </section>

      {/* App section */}
      <section className={styles.section}>
        <p className={styles.sectionLabel}>App</p>
        <div className={styles.card}>
          <div className={`${styles.row} ${styles.rowDivider}`}>
            <span>Theme</span>
            <span className={styles.rowValue}>Dark</span>
          </div>
          <div className={`${styles.row} ${styles.rowDivider}`}>
            <span>Voice input</span>
            <span className={styles.rowValue}>MediaRecorder API</span>
          </div>
          <div className={styles.row}>
            <span>Voice output</span>
            <span className={styles.rowValue}>SpeechSynthesis API</span>
          </div>
        </div>
      </section>

      {/* About section — T26 */}
      <section className={styles.section}>
        <p className={styles.sectionLabel}>About</p>
        <div className={styles.card}>

          {/* T26 — Expandable About VoidFill row */}
          <div
            className={`${styles.row} ${styles.rowDivider} ${styles.rowTappable}`}
            onClick={() => setAboutOpen((o) => !o)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && setAboutOpen((o) => !o)}
            aria-expanded={aboutOpen}
          >
            <span>About VoidFill</span>
            <ChevronIcon rotated={aboutOpen} />
          </div>
          {aboutOpen && (
            <div className={styles.aboutExpanded}>
              <p className={styles.aboutVersion}>v0.1.0</p>
              <p className={styles.aboutText}>
                VoidFill is a voice-first AI co-pilot that fills your free time with
                purpose. Speak your routine and goals once — VoidFill detects every gap
                in your day and suggests what to do next, hands-free.
              </p>
            </div>
          )}

          <div className={`${styles.row} ${styles.rowDivider}`}>
            <span>Version</span>
            <span className={styles.rowValue}>0.1.0</span>
          </div>
          <div className={styles.row}>
            <span>Backend</span>
            <span className={styles.rowValue}>FastAPI · Docker</span>
          </div>
        </div>
      </section>

      {/* Intelligence section */}
      <section className={styles.section}>
        <p className={styles.sectionLabel}>Intelligence</p>
        <div className={styles.card}>
          <div className={styles.row}>
            <div style={{ flex: 1, paddingRight: 12 }}>
              <span className={styles.rowLabel}>Let VoidFill act for me</span>
              <p className={styles.rowSub}>
                Automatically schedules your best next action when a free slot opens
              </p>
            </div>
            <div
              className={`${styles.toggleTrack} ${autonomyEnabled ? styles.toggleActive : ''}`}
              onClick={handleAutonomyToggle}
              role="switch"
              aria-checked={autonomyEnabled}
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && handleAutonomyToggle()}
              style={{ cursor: 'pointer' }}
            >
              <div className={`${styles.toggleThumb} ${autonomyEnabled ? styles.toggleThumbActive : ''}`} />
            </div>
          </div>
        </div>
      </section>

      {/* T27 — Notifications (disabled) */}
      <section className={styles.section}>
        <p className={styles.sectionLabel}>Preferences</p>
        <div className={`${styles.card} ${styles.cardDisabled}`}>
          <div className={styles.row}>
            <div>
              <span className={styles.rowLabel}>Notifications</span>
              <p className={styles.rowSub}>Coming soon</p>
            </div>
            <div className={styles.toggleTrack}>
              <div className={styles.toggleThumb} />
            </div>
          </div>
        </div>
      </section>

      {/* Tagline */}
      <p className={styles.tagline}>VoidFill — use your free time well.</p>

      {/* T25 — Reset confirmation modal */}
      {showResetModal && (
        <div className={styles.modalOverlay} onClick={() => setShowResetModal(false)}>
          <div className={styles.modalCard} onClick={(e) => e.stopPropagation()}>
            <h2 className={styles.modalTitle}>Reset everything?</h2>
            <p className={styles.modalBody}>
              This clears your routine, goals, and all saved data. You'll start from scratch.
            </p>
            <div className={styles.modalActions}>
              <button
                className={styles.modalCancel}
                onClick={() => setShowResetModal(false)}
              >
                Cancel
              </button>
              <button
                className={styles.modalConfirm}
                onClick={handleReset}
              >
                Reset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

