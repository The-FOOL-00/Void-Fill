/**
 * useVoiceRecorder — MediaRecorder API hook
 *
 * Records audio via MediaRecorder (NOT Web Speech API).
 * Returns audio as a Blob (webm/ogg, falls back to whatever the browser supports).
 *
 * Usage:
 *   const { state, start, stop, audioBlob, error } = useVoiceRecorder();
 */

import { useState, useRef, useCallback } from 'react';

export type RecorderState = 'idle' | 'recording' | 'stopped' | 'error';

interface UseVoiceRecorderReturn {
  state: RecorderState;
  start: () => Promise<void>;
  stop: () => void;
  audioBlob: Blob | null;
  audioUrl: string | null;
  durationMs: number;
  error: string | null;
  reset: () => void;
}

export function useVoiceRecorder(): UseVoiceRecorderReturn {
  const [state, setState] = useState<RecorderState>('idle');
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [durationMs, setDurationMs] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const startTimeRef = useRef<number>(0);

  const start = useCallback(async () => {
    try {
      setError(null);
      setAudioBlob(null);
      setAudioUrl(null);
      chunksRef.current = [];

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Pick best supported mime type
      const mimeType = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/ogg',
        'audio/mp4',
      ].find((t) => MediaRecorder.isTypeSupported(t)) ?? '';

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType || 'audio/webm' });
        const url = URL.createObjectURL(blob);
        setAudioBlob(blob);
        setAudioUrl(url);
        setDurationMs(Date.now() - startTimeRef.current);
        setState('stopped');

        // Release microphone
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.onerror = () => {
        setState('error');
        setError('Recording failed. Please try again.');
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.start(250); // Collect data every 250ms
      startTimeRef.current = Date.now();
      setState('recording');
    } catch (err) {
      setState('error');
      if (err instanceof DOMException && err.name === 'NotAllowedError') {
        setError('Microphone access denied. Please allow microphone access and try again.');
      } else {
        setError('Could not start recording. Check your microphone.');
      }
    }
  }, []);

  const stop = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const reset = useCallback(() => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioBlob(null);
    setAudioUrl(null);
    setDurationMs(0);
    setError(null);
    setState('idle');
    chunksRef.current = [];
  }, [audioUrl]);

  return { state, start, stop, audioBlob, audioUrl, durationMs, error, reset };
}
