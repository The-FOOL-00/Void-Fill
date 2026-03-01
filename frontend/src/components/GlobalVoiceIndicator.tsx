/**
 * GlobalVoiceIndicator — fixed red pulsing dot in the top-right
 * corner when a recording is active anywhere in the app.
 */

import { useVoiceContext } from '../context/VoiceContext'
import styles from './GlobalVoiceIndicator.module.css'

export default function GlobalVoiceIndicator() {
  const { state } = useVoiceContext()

  if (state !== 'recording') return null

  return <div className={styles.dot} aria-label="Recording in progress" />
}
