import { Navigate } from 'react-router-dom'

/**
 * Protects routes that require authentication or demo mode.
 * Allows through if authToken exists OR if user chose demo mode
 * (onboardingComplete is set, meaning they went through the skip flow).
 * The backend falls back to a DEMO_USER_ID when no token is present.
 */
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const hasToken = !!localStorage.getItem('authToken')
  const isDemoUser = localStorage.getItem('demoMode') === 'true'
  if (!hasToken && !isDemoUser) return <Navigate to="/auth" replace />
  return <>{children}</>
}
