/**
 * MicPermissionOverlay — full-screen blocking overlay shown when
 * microphone permission has been denied by the user.
 */

import { useVoiceContext } from '../context/VoiceContext'
import styles from './MicPermissionOverlay.module.css'

export default function MicPermissionOverlay() {
  const { micDenied } = useVoiceContext()

  if (!micDenied) return null

  return (
    <div className={styles.overlay}>
      <div className={styles.card}>
        <div className={styles.icon}>🎙️</div>
        <h2 className={styles.heading}>Microphone access required</h2>
        <p className={styles.body}>
          VoidFill needs mic access to work. Please enable it in your browser
          settings — then refresh the page.
        </p>
        <a
          className={styles.link}
          href="https://support.google.com/chrome/answer/2693767"
          target="_blank"
          rel="noopener noreferrer"
        >
          How to enable
        </a>
      </div>
    </div>
  )
}
