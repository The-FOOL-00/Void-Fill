import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { VoiceProvider } from './context/VoiceContext'

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

// Shared layout shell (bottom nav)
import AppShell from './components/AppShell'

/** Redirects / based on localStorage.onboardingComplete (T01/T31) */
function RootRedirect() {
  const navigate = useNavigate()
  useEffect(() => {
    if (localStorage.getItem('onboardingComplete') === 'true') {
      navigate('/home', { replace: true })
    } else {
      navigate('/onboarding', { replace: true })
    }
  }, [navigate])
  return null
}

/** Listens for auth:expired events and redirects to onboarding (T29) */
function AuthExpiredHandler() {
  const navigate = useNavigate()
  useEffect(() => {
    const handler = () => setTimeout(() => navigate('/onboarding'), 1500)
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
          {/* Default → localStorage check */}
          <Route index element={<RootRedirect />} />

          {/* Onboarding lives outside AppShell — no bottom nav */}
          <Route path="/onboarding" element={<OnboardingPage />} />

          {/* Main app pages wrapped in AppShell (bottom nav) */}
          <Route element={<AppShell />}>
            <Route path="/home" element={<HomePage />} />
            <Route path="/voice" element={<VoicePage />} />
            <Route path="/goals" element={<GoalsPage />} />
            <Route path="/reflection" element={<ReflectionPage />} />
            <Route path="/suggestions" element={<Navigate to="/reflection" replace />} />
            <Route path="/schedule" element={<SchedulePage />} />
            <Route path="/notes" element={<NotesPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </VoiceProvider>
    </BrowserRouter>
  )
}
