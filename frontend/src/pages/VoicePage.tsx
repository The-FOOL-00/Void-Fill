import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import { useVoiceRecorder } from '../hooks/useVoiceRecorder'
import type { VoiceIntelligenceResponse } from '../types/api'
import styles from './VoicePage.module.css'

type Phase = 'idle' | 'recording' | 'processing' | 'result' | 'error'

function MicIcon({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="17" x2="12" y2="22" />
      <line x1="8"  y1="22" x2="16" y2="22" />
    </svg>
  )
}

function WaveformIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M2 12h2M6 6v12M10 9v6M14 4v16M18 7v10M22 12h-2" />
    </svg>
  )
}

export default function VoicePage() {
  const [phase, setPhase] = useState<Phase>('idle')
  const [intelligence, setIntelligence] = useState<VoiceIntelligenceResponse | null>(null)
  const [errorMsg, setErrorMsg] = useState('')

  const { state: recState, start, stop, audioBlob } = useVoiceRecorder()

  const handleMicPress = useCallback(async () => {
    if (phase === 'recording') {
      stop()
      return
    }
    if (phase !== 'idle' && phase !== 'result') return
    setIntelligence(null)
    setErrorMsg('')
    setPhase('recording')
    await start()
  }, [phase, start, stop])

  // Once blob is ready after stop, upload + poll
  const handleBlobReady = useCallback(async () => {
    if (!audioBlob) return
    setPhase('processing')
    try {
      const upload = await api.voice.upload(audioBlob)

      // Poll for result
      let attempts = 0
      while (attempts < 30) {
        await new Promise(r => setTimeout(r, 1500))
        const result = await api.voice.result(upload.job_id)
        if ((result.status === 'completed' || result.status === 'partial') && result.transcript) break
        if (result.status === 'failed') throw new Error('Transcription failed')
        attempts++
      }

      // Fetch intelligence
      const intel = await api.voice.intelligence(upload.job_id)
      setIntelligence(intel)
      setPhase('result')
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Something went wrong')
      setPhase('error')
    }
  }, [audioBlob])

  // Trigger upload when blob appears after stop
  useEffect(() => {
    if (recState === 'stopped' && audioBlob && phase === 'recording') {
      handleBlobReady()
    }
  }, [recState, audioBlob, phase, handleBlobReady])

  const reset = () => { setPhase('idle'); setIntelligence(null); setErrorMsg('') }

  const isRecording = phase === 'recording'
  const isProcessing = phase === 'processing'

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <h1 className={styles.title}>Voice Lab</h1>
        <p className={styles.subtitle}>Record a thought, task, or update</p>
      </div>

      {/* Central mic area */}
      <div className={styles.stageArea}>
        <button
          className={`${styles.micBtn} ${isRecording ? styles.micBtnActive : ''} ${isProcessing ? styles.micBtnProcessing : ''}`}
          onClick={handleMicPress}
          disabled={isProcessing}
          aria-label={isRecording ? 'Stop recording' : 'Start recording'}
        >
          <MicIcon size={34} />
        </button>

        <p className={styles.stageLabel}>
          {phase === 'idle'     && 'Tap to record'}
          {phase === 'recording' && 'Recording… tap to stop'}
          {phase === 'processing' && 'Analysing…'}
          {phase === 'result'   && 'Done! Record again or tap a card below.'}
          {phase === 'error'    && errorMsg}
        </p>

        {isProcessing && (
          <div className={styles.processingBars}>
            {Array.from({ length: 9 }).map((_, i) => (
              <div key={i} className={styles.bar} style={{ '--i': i } as React.CSSProperties} />
            ))}
          </div>
        )}
      </div>

      {/* Result card */}
      {phase === 'result' && intelligence && (
        <div className={styles.resultSection}>
          {intelligence.extracted_text && (
            <div className={styles.resultCard}>
              <div className={styles.resultCardHead}>
                <WaveformIcon />
                <span>Extracted Text</span>
              </div>
              <p className={styles.resultText}>{intelligence.extracted_text}</p>
            </div>
          )}

          {intelligence.intent && (
            <div className={styles.resultCard}>
              <div className={styles.resultCardHead}>
                <span>⚡</span>
                <span>Detected Intent</span>
              </div>
              <p className={styles.resultText}>{intelligence.intent}</p>
            </div>
          )}

          <button className={styles.resetBtn} onClick={reset}>
            Record Again
          </button>
        </div>
      )}

      {phase === 'error' && (
        <button className={styles.resetBtn} onClick={reset}>Try Again</button>
      )}
    </div>
  )
}
