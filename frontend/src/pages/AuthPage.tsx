import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import styles from './AuthPage.module.css'

type Mode = 'login' | 'register'

export default function AuthPage() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
      const result =
        mode === 'register'
          ? await api.auth.register(email, password, timezone)
          : await api.auth.login(email, password)

      localStorage.setItem('authToken', result.access_token)
      localStorage.setItem('userId', result.user_id)
      localStorage.setItem('userEmail', email.toLowerCase())

      // New registrations go through onboarding; returning users go home
      if (mode === 'register') {
        localStorage.removeItem('onboardingComplete')
        navigate('/onboarding', { replace: true })
      } else {
        const onboarded = localStorage.getItem('onboardingComplete') === 'true'
        navigate(onboarded ? '/home' : '/onboarding', { replace: true })
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Something went wrong'
      // Parse backend detail out of "API 409: {...}" style messages
      const match = msg.match(/API \d+: (.+)/)
      if (match) {
        try {
          const body = JSON.parse(match[1])
          setError(body.detail ?? match[1])
        } catch {
          setError(match[1])
        }
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }

  const skipAuth = () => {
    // Continue as the anonymous demo user (no token)
    const onboarded = localStorage.getItem('onboardingComplete') === 'true'
    navigate(onboarded ? '/home' : '/onboarding', { replace: true })
  }

  return (
    <div className={styles.container}>
      <div className={styles.logo}>VoidFill</div>
      <p className={styles.tagline}>Your voice-first AI productivity copilot</p>

      <div className={styles.card}>
        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${mode === 'login' ? styles.active : ''}`}
            onClick={() => { setMode('login'); setError(null) }}
          >
            Sign in
          </button>
          <button
            className={`${styles.tab} ${mode === 'register' ? styles.active : ''}`}
            onClick={() => { setMode('register'); setError(null) }}
          >
            Create account
          </button>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          {error && <div className={styles.error}>{error}</div>}

          <div className={styles.field}>
            <label className={styles.label}>Email</label>
            <input
              className={styles.input}
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Password</label>
            <input
              className={styles.input}
              type="password"
              autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
              placeholder={mode === 'register' ? 'At least 8 characters' : '••••••••'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>

          <button className={styles.submit} type="submit" disabled={loading}>
            {loading ? 'Please wait…' : mode === 'register' ? 'Create account' : 'Sign in'}
          </button>
        </form>

        <div className={styles.skip}>
          <button className={styles.skipLink} onClick={skipAuth}>
            Continue without an account
          </button>
        </div>
      </div>
    </div>
  )
}
