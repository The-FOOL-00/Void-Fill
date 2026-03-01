/**
 * Central API client for VoidFill backend.
 * All calls go through /api/v1 — proxied to localhost:8000 by Vite.
 * Auth is stubbed on the backend (returns DEMO_USER_ID), so no headers needed.
 */

const BASE = '/api/v1';

async function http<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });
  } catch {
    window.dispatchEvent(new CustomEvent('api:offline'));
    throw new Error(`Network error: ${path}`);
  }

  // 401 — session expired
  if (res.status === 401) {
    localStorage.removeItem('authToken');
    window.dispatchEvent(new CustomEvent('auth:expired'));
  }

  if (!res.ok) {
    if (res.status >= 500) {
      window.dispatchEvent(new CustomEvent('api:offline'));
    }
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }

  // 2xx success — signal online
  window.dispatchEvent(new CustomEvent('api:online'));

  // 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Multipart helper (for audio upload) ───────────────────────────────────
async function httpForm<T>(path: string, form: FormData): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      method: 'POST',
      body: form,
      // Do NOT set Content-Type — let browser set multipart boundary
    });
  } catch {
    window.dispatchEvent(new CustomEvent('api:offline'));
    throw new Error(`Network error: ${path}`);
  }

  if (!res.ok) {
    if (res.status >= 500) {
      window.dispatchEvent(new CustomEvent('api:offline'));
    }
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }

  window.dispatchEvent(new CustomEvent('api:online'));
  return res.json() as Promise<T>;
}

export const api = {
  // ── Voice ──────────────────────────────────────────────────────────────
  voice: {
    upload: (file: Blob, filename = 'recording.webm') => {
      const form = new FormData();
      form.append('file', file, filename);
      return httpForm<import('@/types/api').VoiceUploadResponse>('/voice/upload', form);
    },
    result: (jobId: string) =>
      http<import('@/types/api').VoiceResultResponse>(`/voice/result/${jobId}`),
    intelligence: (jobId: string) =>
      http<import('@/types/api').VoiceIntelligenceResponse>(`/voice/intelligence/${jobId}`),
  },

  // ── Goals ──────────────────────────────────────────────────────────────
  goals: {
    list: () =>
      http<import('@/types/api').GoalListResponse>('/goals'),
    create: (payload: import('@/types/api').GoalCreate) =>
      http<import('@/types/api').Goal>('/goals', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    search: (query: string, limit = 5) =>
      http<import('@/types/api').GoalSearchResult[]>('/goals/search', {
        method: 'POST',
        body: JSON.stringify({ query, limit }),
      }),
    parseAndCreate: (transcript: string) =>
      http<import('@/types/api').GoalParseAndCreateResponse>('/goals/parse-and-create', {
        method: 'POST',
        body: JSON.stringify({ transcript }),
      }),
    weeklyFocus: (transcript: string) =>
      http<import('@/types/api').WeeklyFocusResponse>('/goals/weekly-focus', {
        method: 'POST',
        body: JSON.stringify({ transcript }),
      }),
  },

  // ── Suggestions ────────────────────────────────────────────────────────
  suggestions: {
    request: (payload: import('@/types/api').SuggestionRequest = {}) =>
      http<import('@/types/api').SuggestionListResponse>('/suggestions/request', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    /**
     * Accept a suggestion. Backend endpoint does NOT exist yet —
     * logs to console and returns a stub response.
     */
    accept: async (suggestionId: string): Promise<import('@/types/api').SuggestionAcceptResponse> => {
      console.warn('[suggestions.accept] stub — backend endpoint not implemented', { suggestionId });
      // TODO: uncomment when POST /suggestions/accept exists
      // return http<import('@/types/api').SuggestionAcceptResponse>('/suggestions/accept', {
      //   method: 'POST',
      //   body: JSON.stringify({ suggestion_id: suggestionId }),
      // });
      return { status: 'accepted' };
    },

    /**
     * Skip multiple suggestions. Backend endpoint does NOT exist yet —
     * logs to console and returns a stub response.
     */
    skip: async (suggestionIds: string[]): Promise<import('@/types/api').SuggestionSkipResponse> => {
      console.warn('[suggestions.skip] stub — backend endpoint not implemented', { suggestionIds });
      // TODO: uncomment when POST /suggestions/skip exists
      // return http<import('@/types/api').SuggestionSkipResponse>('/suggestions/skip', {
      //   method: 'POST',
      //   body: JSON.stringify({ suggestion_ids: suggestionIds }),
      // });
      return { status: 'skipped' };
    },
  },

  // ── Notes ──────────────────────────────────────────────────────────────
  notes: {
    list: () =>
      http<import('@/types/api').NoteListResponse>('/notes'),
  },

  // ── Schedule ───────────────────────────────────────────────────────────
  schedule: {
    list: () =>
      http<import('@/types/api').ScheduleBlockListResponse>('/schedule'),
    create: (payload: import('@/types/api').ScheduleBlockCreate) =>
      http<import('@/types/api').ScheduleBlock>('/schedule', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),    delete: (blockId: string) =>
      http<void>(`/schedule/${blockId}`, { method: 'DELETE' }),  },

  // ── Void ─────────────────────────────────────────────────────────────────
  void: {
    now: () =>
      http<import('@/types/api').VoidNowResponse>('/void/now'),
    plan: () =>
      http<import('@/types/api').VoidPlanResponse>('/void/plan'),
  },

  // ── Autonomy Engine ───────────────────────────────────────────────────────
  autonomy: {
    run: () =>
      http<import('@/types/api').AutonomyResponse>('/autonomy/run', { method: 'POST' }),
  },

  // ── Habits ────────────────────────────────────────────────────────────────
  habits: {
    summary: () =>
      http<import('@/types/api').HabitSummaryResponse>('/habits/summary'),
  },

  // ── Memory ────────────────────────────────────────────────────────────────
  memory: {
    summary: () =>
      http<import('@/types/api').MemorySummaryResponse>('/memory/summary'),
    create: (payload: import('@/types/api').MemoryRecordRequest) =>
      http<{ status: string }>('/memory', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
  },

  // ── Reflection ────────────────────────────────────────────────────────────
  reflection: {
    latest: () =>
      http<import('@/types/api').ReflectionResponse>('/reflection/latest'),
  },

};
