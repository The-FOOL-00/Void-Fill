import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/global.css'
import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'

// ---------------------------------------------------------------------------
// Optional: Sentry frontend error reporting
// Uncomment after running: npm install @sentry/react
// Set VITE_SENTRY_DSN in Railway environment variables.
// ---------------------------------------------------------------------------
// import * as Sentry from '@sentry/react'
// if (import.meta.env.VITE_SENTRY_DSN) {
//   Sentry.init({
//     dsn: import.meta.env.VITE_SENTRY_DSN,
//     environment: import.meta.env.MODE,
//     tracesSampleRate: 0.1,
//   })
//   // Expose capture for ErrorBoundary (class components can't use hooks)
//   ;(window as Window & { __sentryCapture?: (e: Error) => string }).__sentryCapture =
//     (error: Error) => {
//       const eventId = Sentry.captureException(error)
//       return eventId
//     }
// }

// ── Service Worker registration (PWA / WebAPK) ────────────────────────────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .then((reg) => console.log('[SW] Registered:', reg.scope))
      .catch((err) => console.warn('[SW] Registration failed:', err))
  })
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)

