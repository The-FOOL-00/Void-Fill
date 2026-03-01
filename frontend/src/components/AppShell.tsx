import { useState, useEffect } from 'react'
import { Outlet, NavLink } from 'react-router-dom'
import GlobalVoiceIndicator from './GlobalVoiceIndicator'
import MicPermissionOverlay from './MicPermissionOverlay'
import styles from './AppShell.module.css'

// ── SVG Nav Icons ──────────────────────────────────────────────────────────
function IconHome({ active }: { active: boolean }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={active ? '#ED1C24' : '#555'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z" />
      <path d="M9 21V12h6v9" />
    </svg>
  )
}

function IconTarget({ active }: { active: boolean }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={active ? '#ED1C24' : '#555'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  )
}

function IconSparkle({ active }: { active: boolean }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill={active ? '#ED1C24' : '#555'} stroke="none">
      <path d="M12 2l2.09 6.26L20 10l-5.91 1.74L12 18l-2.09-6.26L4 10l5.91-1.74L12 2z" />
      <path d="M19 17l.9 2.1L22 20l-2.1.9L19 23l-.9-2.1L16 20l2.1-.9L19 17z" opacity="0.6" />
      <path d="M5 3l.7 1.6L7 5l-1.3.4L5 7l-.7-1.6L3 5l1.3-.4L5 3z" opacity="0.6" />
    </svg>
  )
}

function IconSettings({ active }: { active: boolean }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={active ? '#ED1C24' : '#555'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

const NAV_ITEMS = [
  { to: '/home',        Icon: IconHome     },
  { to: '/goals',       Icon: IconTarget   },
  { to: '/reflection',  Icon: IconSparkle  },
  { to: '/settings',    Icon: IconSettings },
]

export default function AppShell() {
  const [showOfflineBanner, setShowOfflineBanner] = useState(false)

  useEffect(() => {
    const onOffline = () => setShowOfflineBanner(true)
    const onOnline  = () => setShowOfflineBanner(false)
    window.addEventListener('api:offline', onOffline)
    window.addEventListener('api:online',  onOnline)
    return () => {
      window.removeEventListener('api:offline', onOffline)
      window.removeEventListener('api:online',  onOnline)
    }
  }, [])

  return (
    <div className={styles.shell}>
      <GlobalVoiceIndicator />
      <MicPermissionOverlay />

      {showOfflineBanner && (
        <div className={styles.offlineBanner}>
          Can’t reach server — some features limited
        </div>
      )}

      <main className={styles.main}>
        <Outlet />
      </main>

      <nav
        className={styles.nav}
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      >
        {NAV_ITEMS.map(({ to, Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `${styles.navItem} ${isActive ? styles.navItemActive : ''}`
            }
          >
            {({ isActive }) => <Icon active={isActive} />}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
