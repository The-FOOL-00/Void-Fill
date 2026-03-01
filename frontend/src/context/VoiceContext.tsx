/**
 * VoiceContext — global recording state
 *
 * Ensures only one recording at a time across all screens.
 * Cancels active TTS before starting a new recording.
 * Exposes `micDenied` boolean when the user has blocked mic access.
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  type ReactNode,
} from 'react'

// ── Types ────────────────────────────────────────────────────────────────────
export type RecorderState = 'idle' | 'recording' | 'stopped' | 'error'

interface VoiceContextValue {
  /** Current recorder state */
  state: RecorderState
  /** ID of the component that owns the active recording (null if idle) */
  activeRecorderId: string | null
  /** true while the user has denied mic permission */
  micDenied: boolean
  /** The recorded audio blob (available after stop) */
  audioBlob: Blob | null
  /** Duration of the last recording in ms */
  durationMs: number
  /** Last error message (if any) */
  error: string | null
  /** Start recording — cancels active TTS and any prior recording first */
  startRecording: (recorderId: string) => Promise<void>
  /** Stop the active recording */
  stopRecording: () => void
  /** Reset back to idle */
  resetRecording: () => void
}

const VoiceContext = createContext<VoiceContextValue | null>(null)

// ── Provider ─────────────────────────────────────────────────────────────────
export function VoiceProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<RecorderState>('idle')
  const [activeRecorderId, setActiveRecorderId] = useState<string | null>(null)
  const [micDenied, setMicDenied] = useState(false)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [durationMs, setDurationMs] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const startTimeRef = useRef(0)

  // ── helpers ──────────────────────────────────────────────────────────────
  const releaseStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }, [])

  const cancelTTS = useCallback(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
  }, [])

  // ── startRecording ───────────────────────────────────────────────────────
  const startRecording = useCallback(
    async (recorderId: string) => {
      // Cancel any active TTS first
      cancelTTS()

      // Stop existing recording if one is active
      if (
        mediaRecorderRef.current &&
        mediaRecorderRef.current.state !== 'inactive'
      ) {
        mediaRecorderRef.current.stop()
        releaseStream()
      }

      // Reset state
      setError(null)
      setAudioBlob(null)
      setDurationMs(0)
      chunksRef.current = []

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        })
        streamRef.current = stream

        // If we got here, mic is not denied
        setMicDenied(false)

        const mimeType =
          [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/ogg',
            'audio/mp4',
          ].find((t) => MediaRecorder.isTypeSupported(t)) ?? ''

        const recorder = new MediaRecorder(
          stream,
          mimeType ? { mimeType } : undefined,
        )
        mediaRecorderRef.current = recorder

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) chunksRef.current.push(e.data)
        }

        recorder.onstop = () => {
          const blob = new Blob(chunksRef.current, {
            type: mimeType || 'audio/webm',
          })
          setAudioBlob(blob)
          setDurationMs(Date.now() - startTimeRef.current)
          setState('stopped')
          releaseStream()
        }

        recorder.onerror = () => {
          setState('error')
          setError('Recording failed. Please try again.')
          releaseStream()
        }

        recorder.start(250)
        startTimeRef.current = Date.now()
        setState('recording')
        setActiveRecorderId(recorderId)
      } catch (err) {
        setState('error')
        if (
          err instanceof DOMException &&
          (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError')
        ) {
          setMicDenied(true)
          setError(
            'Microphone access denied. Please allow microphone access and try again.',
          )
        } else {
          setError('Could not start recording. Check your microphone.')
        }
      }
    },
    [cancelTTS, releaseStream],
  )

  // ── stopRecording ────────────────────────────────────────────────────────
  const stopRecording = useCallback(() => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== 'inactive'
    ) {
      mediaRecorderRef.current.stop()
    }
  }, [])

  // ── resetRecording ───────────────────────────────────────────────────────
  const resetRecording = useCallback(() => {
    setAudioBlob(null)
    setDurationMs(0)
    setError(null)
    setState('idle')
    setActiveRecorderId(null)
    chunksRef.current = []
  }, [])

  return (
    <VoiceContext.Provider
      value={{
        state,
        activeRecorderId,
        micDenied,
        audioBlob,
        durationMs,
        error,
        startRecording,
        stopRecording,
        resetRecording,
      }}
    >
      {children}
    </VoiceContext.Provider>
  )
}

// ── Hook ─────────────────────────────────────────────────────────────────────
export function useVoiceContext(): VoiceContextValue {
  const ctx = useContext(VoiceContext)
  if (!ctx) {
    throw new Error('useVoiceContext must be used inside <VoiceProvider>')
  }
  return ctx
}
