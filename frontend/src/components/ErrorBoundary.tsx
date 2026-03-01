import { Component, type ErrorInfo, type ReactNode } from 'react'
import styles from './ErrorBoundary.module.css'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  eventId: string | null
}

/**
 * Top-level React error boundary.
 *
 * - Development: logs full error + component stack to console.
 * - Production:  logs to console and, if @sentry/react is initialised,
 *   captures the exception via `window.__sentryCapture` (injected by
 *   main.tsx when VITE_SENTRY_DSN is set).
 *
 * To enable frontend Sentry reporting:
 *   npm install @sentry/react
 *   Set VITE_SENTRY_DSN in your Railway environment variables.
 *   Uncomment the Sentry block in main.tsx.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, eventId: null }
  }

  static getDerivedStateFromError(): State {
    return { hasError: true, eventId: null }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (import.meta.env.DEV) {
      // Full details in development
      console.error('[ErrorBoundary] Uncaught render error:', error)
      console.error('[ErrorBoundary] Component stack:', info.componentStack)
    } else {
      // Minimal log in production to avoid leaking internals
      console.error('[ErrorBoundary] Render error:', error.message)

      // Forward to Sentry if the capture function was injected by main.tsx
      const sentryCapture = (window as Window & { __sentryCapture?: (e: Error) => string })
        .__sentryCapture
      if (sentryCapture) {
        const eventId = sentryCapture(error)
        this.setState({ eventId })
      }
    }
  }

  private handleRefresh = (): void => {
    window.location.reload()
  }

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children
    }

    return (
      <div className={styles.container}>
        <div className={styles.card}>
          <div className={styles.icon}>⚠️</div>
          <h2 className={styles.heading}>Something went wrong.</h2>
          <p className={styles.body}>
            An unexpected error occurred. Refresh the page to continue.
          </p>
          {this.state.eventId && (
            <p className={styles.eventId}>Error ID: {this.state.eventId}</p>
          )}
          <button className={styles.button} onClick={this.handleRefresh}>
            Refresh
          </button>
        </div>
      </div>
    )
  }
}
