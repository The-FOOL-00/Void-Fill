import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { VoiceProvider } from './context/VoiceContext'

// Auth — full-bleed, no nav shell
import AuthPage from './pages/AuthPage'

// Onboarding — full-bleed, no nav shell
import OnboardingPage from './pages/OnboardingPage'

// Main app pages
import HomePage from './pages/HomePage'
import VoicePage from './pages/VoicePage'
import GoalsPage from './pages/GoalsPage'
import ReflectionPage from './pages/ReflectionPage'
import SchedulePage from './pages/SchedulePage'
import NotesPage from './pages/NotesPage'
import SettingsPage from './pages/SettingsPage'
import HabitsPage from './pages/HabitsPage'
import MemoryPage from './pages/MemoryPage'

// Shared layout shell (bottom nav)
import AppShell from './components/AppShell'
import AuthGuard from './components/AuthGuard'

/** Redirects / based on authToken + onboardingComplete */
function RootRedirect() {
  const navigate = useNavigate()
  useEffect(() => {
    const hasToken = !!localStorage.getItem('authToken')
    const isDemoUser = localStorage.getItem('demoMode') === 'true'
    const onboarded = localStorage.getItem('onboardingComplete') === 'true'
    if (!hasToken && !isDemoUser) {
      // No account and not demo — show auth page
      navigate('/auth', { replace: true })
    } else if (!onboarded) {
      navigate('/onboarding', { replace: true })
    } else {
      navigate('/home', { replace: true })
    }
  }, [navigate])
  return null
}

/** Redirects to /auth on token expiry */
function AuthExpiredHandler() {
  const navigate = useNavigate()
  useEffect(() => {
    const handler = () => setTimeout(() => navigate('/auth'), 1500)
    window.addEventListener('auth:expired', handler)
    return () => window.removeEventListener('auth:expired', handler)
  }, [navigate])
  return null
}

export default function App() {
  return (
    <BrowserRouter>
      <VoiceProvider>
        <AuthExpiredHandler />
        <Routes>
          {/* Default → token/onboarding check */}
          <Route index element={<RootRedirect />} />

          {/* Auth lives outside AppShell */}
          <Route path="/auth" element={<AuthPage />} />

          {/* Onboarding lives outside AppShell — no bottom nav */}
          <Route path="/onboarding" element={<OnboardingPage />} />

          {/* Main app pages wrapped in AppShell (bottom nav) + auth guard */}
          <Route element={<AuthGuard><AppShell /></AuthGuard>}>
            <Route path="/home" element={<HomePage />} />
            <Route path="/voice" element={<VoicePage />} />
            <Route path="/goals" element={<GoalsPage />} />
            <Route path="/reflection" element={<ReflectionPage />} />
            <Route path="/suggestions" element={<Navigate to="/reflection" replace />} />
            <Route path="/schedule" element={<SchedulePage />} />
            <Route path="/notes" element={<NotesPage />} />
            <Route path="/habits" element={<HabitsPage />} />
            <Route path="/memory" element={<MemoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </VoiceProvider>
    </BrowserRouter>
  )
}
