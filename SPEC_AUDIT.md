# VoidFill Spec Audit — v1.0
**Date:** 2026-02-28  
**Reference:** Complete App Flow & Interaction Specification v1.0

---

## ✅ DONE — Complete Implementation Log

### Infrastructure & Config
- ✅ Vite 6 + React 18 + TypeScript (strict) project scaffold
- ✅ `vite.config.ts` — port 3000, `/api` proxied to `localhost:8000`
- ✅ `tsconfig.json` — strict mode, `@/*` path alias
- ✅ `index.html` — Poppins font via Google Fonts
- ✅ `src/styles/global.css` — full CSS design token system (`--color-bg`, `--color-accent: #ED1C24`, `--color-surface`, `--radius-*`, `--space-*`, `--font-size-*`, `--transition-*`)
- ✅ `src/vite-env.d.ts` — CSS module type declarations
- ✅ All TypeScript checks pass: `npx tsc --noEmit` → EXIT:0

### Types (`src/types/api.ts`)
- ✅ `VoiceUploadResponse` — `{ job_id, status }`
- ✅ `VoiceResultResponse` — `{ job_id, status, transcript, created_at, updated_at }`
- ✅ `VoiceIntelligenceResponse` — `{ id, job_id, intent, extracted_text, matched_goal_id, created_at }`
- ✅ `Goal`, `GoalCreate`, `GoalListResponse`, `GoalSearchResult`
- ✅ `Suggestion`, `SuggestionListResponse`, `SuggestionRequest`
- ✅ `Note`, `NoteListResponse`
- ✅ `ScheduleBlock`, `ScheduleBlockCreate`, `ScheduleBlockListResponse`
- ✅ `VoidSlot` — `{ start_time, end_time, duration_minutes, message }`

### API Client (`src/api/client.ts`)
- ✅ `api.voice.upload(blob)` → `POST /voice/upload` (multipart, no manual Content-Type)
- ✅ `api.voice.result(jobId)` → `GET /voice/result/{job_id}`
- ✅ `api.voice.intelligence(jobId)` → `GET /voice/intelligence/{job_id}`
- ✅ `api.goals.list()` → `GET /goals`
- ✅ `api.goals.create(payload)` → `POST /goals`
- ✅ `api.goals.search(query, limit)` → `POST /goals/search`
- ✅ `api.suggestions.request(payload)` → `POST /suggestions/request`
- ✅ `api.notes.list()` → `GET /notes`
- ✅ `api.schedule.list()` → `GET /schedule`
- ✅ `api.schedule.create(payload)` → `POST /schedule`
- ✅ `api.void.current()` → `GET /void/current`

### Hooks
- ✅ `useVoiceRecorder` — full MediaRecorder API hook
  - States: `idle | recording | stopped | error`
  - Picks best MIME type (webm/opus → webm → ogg/opus → ogg → mp4)
  - Collects chunks every 250ms
  - Releases microphone tracks on stop
  - Returns `{ state, start, stop, audioBlob, audioUrl, durationMs, error, reset }`
- ✅ `useSpeechOutput` — SpeechSynthesis wrapper
  - Returns `{ speak, cancel, isSpeaking, isSupported }`

### App Shell & Routing (`src/App.tsx` + `AppShell.tsx`)
- ✅ `BrowserRouter` with `Routes`
- ✅ Default `/` → redirect to `/onboarding`
- ✅ `/onboarding` renders outside AppShell (no bottom nav)
- ✅ AppShell wraps `/home`, `/voice`, `/goals`, `/suggestions`, `/schedule`, `/notes`, `/settings`
- ✅ `AppShell.tsx` — 4-icon SVG bottom nav (Home, Target, Sparkle, Gear)
- ✅ Active route icon turns `#ED1C24` (AMD red) via `NavLink` render prop
- ✅ Layout: `height: 100dvh`, `main` flex-grows, nav fixed at bottom
- ✅ `max-width: 480px; margin: 0 auto` — mobile-width container

### Onboarding Screen (`OnboardingPage.tsx` + `.module.css`)
- ✅ 3-step flow (Your Routine → Your Goals → Your Focus)
- ✅ Top progress bar — active step = white expanding pill (`flex: 3`), done = white dot, future = grey dot
- ✅ Step label: "Step X of 3 — [Phase]"
- ✅ Large heading per step
- ✅ Subtitle per step
- ✅ Mic ring button — dark background, 164px outer ring
- ✅ Recording state — ring turns red + `pulse` keyframe animation
- ✅ Spinner (`LoadingSpinner` SVG with `animateTransform`) shown while polling
- ✅ After recording stops: uploads to `POST /voice/upload`, polls every 1500ms (max 20 attempts)
- ✅ Transcript shown in sliding bottom drawer
- ✅ Drawer labels: LISTENING → PROCESSING → CAPTURED
- ✅ Continue/Next button renders only after transcript received (`canAdvance`)
- ✅ Step 3 (final) — button text changes to "Get Started" → navigates to `/home`
- ✅ Pagination dots at bottom (3 dots, active = red)
- ✅ **Skip button** — top-right "Skip" → `navigate('/home')` immediately (added per user request)
- ✅ Error text shown for `error` from recorder hook
- ❌ `localStorage.setItem('onboardingComplete', 'true')` NOT set on completion
- ❌ `localStorage.setItem('routineTranscript', ...)` NOT saved
- ❌ `localStorage.setItem('goalsTranscript', ...)` NOT saved
- ❌ No `POST /api/v1/schedule/parse` call after Step 1 Continue
- ❌ No `POST /api/v1/goals/parse` + `POST /api/v1/goals/bulk` after Step 2 Continue
- ❌ Step 3 is a voice step ("When do you do your best work?"), NOT the spec's confirmation screen
- ❌ No Step 3 confirmation screen with schedule summary + goals summary cards
- ❌ No "Edit" icons on Step 3 cards to go back to Step 1 or 2
- ❌ No "Start over" ghost button
- ❌ No category dots lighting up on Step 2 (keyword detection + visual feedback)
- ❌ App launch check (localStorage `onboardingComplete`) missing from App.tsx

### Home Screen (`HomePage.tsx` + `.module.css`)
- ✅ Time-based greeting ("Good morning/afternoon/evening")
- ✅ Hardcoded name "Arjun" (placeholder — should read from `localStorage.userName`)
- ✅ Red ECG `PulseIcon` SVG next to greeting
- ✅ Fetches `GET /void/current` → displays free time headline
- ✅ Fetches `GET /schedule` → finds next upcoming block for "Next up" subtitle
- ✅ Large circular mic button — dark background, multi-layer red `box-shadow` glow ring
- ✅ Tapping mic → calls `POST /suggestions/request({})` → shows 3 suggestion cards
- ✅ `SuggestionCard` — 4px left accent bar, category icon, title + meta
- ✅ Category colors: Academic=`#ED1C24`, Career=`#3B82F6`, Health=`#10B981`, Personal=`#A855F7`
- ✅ Skeleton shimmer loaders while loading
- ✅ `micBtnPulsing` animation while fetching suggestions
- ❌ Does NOT read `scheduleSkeleton` from localStorage; fetches fresh from API only
- ❌ Screen State B (no void pocket / inside a fixed block) not implemented — mic is always tappable
- ❌ No voice recording on home mic — just fetches suggestions directly; spec requires record → upload → transcript → then POST /suggestions with transcript + void_duration + time_of_day
- ❌ No global red pulsing dot indicator in top-right corner when recording
- ❌ No suggestion overlay (modal) — spec requires slide-up modal with blur background
- ❌ Suggestion cards are display-only with no overlay interaction (select, "Let's do it", "Not now")
- ❌ No SpeechSynthesis auto-reading suggestions after overlay appears
- ❌ Cards don't show `reason` field from API (spec item 63)
- ❌ No `POST /suggestions/accept` or `POST /suggestions/skip` API calls
- ❌ No "accepted" card green tint state after confirmation
- ❌ Screen State C (first open post-onboarding empty state card) not implemented
- ❌ `voidSlot.message` used as "Next up" fallback — should read `scheduleSkeleton` from localStorage

### Goals Screen (`GoalsPage.tsx` + `.module.css`)
- ✅ Fetches `GET /goals` on mount
- ✅ Skeleton shimmer loading state on all 4 cards
- ✅ 2×2 CSS grid layout
- ✅ 4 category bucket cards (Academic, Career, Personal Growth, Health & Rest)
- ✅ `categorizeGoal()` keyword-based categorization
- ✅ Colored 3px top border bar per card
- ✅ Translucent category icon circle (`color-mix()` for bg)
- ✅ Goals listed per card (newest logic via `updated_at`)
- ✅ "Updated X ago" timestamp
- ✅ Tap card → starts recording for that category (`activeCard` state)
- ✅ Card gets outline glow when active (`cardActive` state)
- ✅ "🎙 Listening…" badge on active card
- ✅ Upload → poll transcript → `POST /goals` → refresh goals list
- ✅ Status message: "Goal added!" for 2s
- ✅ "What's your focus this week?" CTA card with mic
- ✅ CTA mic turns solid red when recording
- ❌ No header-level mic button for multi-category goal entry (`POST /goals/parse-and-create`)
- ❌ No optimistic UI update (goal appears immediately with loading dot before API confirms)
- ❌ Goals not saved to `localStorage` as `cachedGoals` after successful fetch
- ❌ No fallback to `cachedGoals` when API fails; no "Showing cached goals — tap to retry" banner
- ❌ CTA card voice result calls wrong endpoint — uses `POST /goals` not `POST /goals/weekly-focus`
- ❌ `weeklyFocus` not saved to `localStorage` after CTA recording
- ❌ Only one recording hook instance — concurrent card recording cancels the active card but doesn't cleanly signal the UI (spec req: stop previous before starting new)

### Weekly Reflection / Suggestions Screen (`SuggestionsPage.tsx` + `.module.css`)
- ✅ Header "Weekly Reflection" + CalendarIcon SVG
- ✅ Date label (formatted today's date)
- ✅ "This Week in Review" card with 18 animated waveform bars
- ✅ CSS `waveBar` animation with per-bar stagger via `--bar-delay`
- ✅ Play/Pause button (56px circle) — fake 5s playback via `setTimeout`
- ✅ 4 category stat rows — colored dot, bold name, "X sessions · Y hrs"
- ✅ "0 sessions" row shows red text
- ✅ Priority insight card — lightning icon, weakest category text
- ✅ CTA "Generate New Suggestions" button → calls `POST /suggestions/request`
- ❌ Route is `/suggestions` — spec says `/reflection`; nav icon should link to `/reflection`
- ❌ Fetches `GET /goals` + `POST /suggestions/request` to derive stats — spec requires `GET /api/v1/reflection/latest` returning real reflection data
- ❌ No empty state (spec: "Your first reflection will be ready after your first week of use")
- ❌ Play button uses fake `setTimeout` — spec requires actual `audio_url` via HTML Audio, or SpeechSynthesis fallback for `summary_text`
- ❌ No Pause functionality (pause HTML Audio / cancel SpeechSynthesis)
- ❌ No "Update Goals for Next Week" button with recording flow
- ❌ Stats are derived from goal count arithmetic — not from real `reflection.stats[]` array

### Voice Screen (`VoicePage.tsx` + `.module.css`)
- ✅ "Voice Lab" header with subtitle
- ✅ Central 148px mic button — red glow ring (reuses HomePage mic style)
- ✅ States: idle → recording → processing → result → error
- ✅ Animated processing waveform bars (9 bars, stagger animation)
- ✅ Shows `intelligence.extracted_text` and `intelligence.intent` after processing
- ✅ "Record Again" reset button
- ✅ Error state with "Try Again"
- ⚠️ This screen is not in the spec — spec does not define a `/voice` route. The spec's
   voice functionality exists inline on each screen (home, goals, reflection). Consider repurposing
   or removing this route; the nav icon currently links to it but the spec has no such destination.

### Schedule Screen (`SchedulePage.tsx` + `.module.css`)
- ✅ Header "Schedule" + CalendarIcon
- ✅ Today's date label
- ✅ Fetches `GET /schedule` + `GET /void/current`
- ✅ Green void banner with duration
- ✅ Timeline list of blocks, sorted by `start_time`
- ✅ 4px left accent bar with colour derived from block title keywords
- ✅ Block time range, title, and duration label
- ✅ Skeleton loaders while fetching
- ✅ Empty state text
- ✅ Red mic FAB for recording new schedule block
- ✅ FAB pulses when recording, dims when processing
- ⚠️ Not in spec as a primary nav destination — spec's schedule info is embedded in Home and Onboarding Step 1

### Notes Screen (`NotesPage.tsx` + `.module.css`)
- ✅ Header "Notes" + NoteIcon
- ✅ Fetches `GET /notes`, sorted newest first
- ✅ Tap-to-expand note cards (shows excerpt when collapsed, full text when open)
- ✅ 4px red left accent bar per card
- ✅ Relative time display ("2h ago", "3d ago")
- ✅ Skeleton loaders
- ✅ Empty state
- ✅ Red mic FAB to record a new note
- ⚠️ Not in spec as a primary nav destination

### Settings Screen (`SettingsPage.tsx` + `.module.css`)
- ✅ Header "Settings" + subtitle
- ✅ Profile card with avatar "A", name "Arjun", "Demo account"
- ✅ Goal Categories section — 4 rows with colored dot, icon, label, hex color
- ✅ App section — Theme, Voice input, Voice output info rows
- ✅ About section — Version + Backend rows
- ✅ "VoidFill — use your free time well." tagline
- ❌ No "Your Name" interactive row (spec: tap to edit inline → saves to `localStorage.userName`)
- ❌ No "Reset Onboarding" row with confirmation dialog → clears localStorage → navigate to `/onboarding`
- ❌ No "About VoidFill" expandable row with version + description
- ❌ No "Notification Preferences" toggle (greyed out, "Coming soon")
- ❌ Profile name not read from `localStorage.userName`

---

## ❌ TODO — Missing Implementation List

### P0 — Core App Logic (Breakage without these)

#### T01 — App Launch localStorage check
**File:** `src/App.tsx`
- Add `useEffect` on mount: read `localStorage.getItem('onboardingComplete')`
- If `'true'` → navigate to `/home`; else → navigate to `/onboarding`
- Replaces the current hard-coded `<Navigate to="/onboarding" replace />`

#### T02 — Onboarding Step 3: Confirmation Screen
**File:** `src/pages/OnboardingPage.tsx`
- Replace current Step 3 voice prompt ("When do you do your best work?") with the spec's confirmation screen
- Show parsed schedule summary (read `scheduleSkeleton` from localStorage) with edit icon
- Show parsed goals summary (read `initialGoals` from localStorage) with edit icon  
- "Looks good, let's start" button → set `localStorage.onboardingComplete = 'true'`, navigate to `/home`
- "Start over" ghost button → confirmation dialog → clear all onboarding localStorage keys → navigate to Step 1
- Edit icons → navigate back to respective step, pre-fill transcript

#### T03 — Onboarding Step 1 Continue: schedule/parse API + localStorage saves
**File:** `src/pages/OnboardingPage.tsx`
- On Step 1 Continue: save transcript to `localStorage.routineTranscript`
- Call `POST /api/v1/schedule/parse` with `{ transcript }`
- Save response to `localStorage.scheduleSkeleton`
- Add endpoint to `api` client: `api.schedule.parse(transcript)`

#### T04 — Onboarding Step 2: category dots + goals/parse + goals/bulk
**File:** `src/pages/OnboardingPage.tsx`
- Run keyword matching on transcript → light up 4 category dots (red/blue/purple/green)
- On Continue: save transcript to `localStorage.goalsTranscript`
- Call `POST /api/v1/goals/parse` with `{ transcript }` → save response to `localStorage.initialGoals`
- Call `POST /api/v1/goals/bulk` with `{ goals }` to persist
- Add endpoints to `api` client: `api.goals.parse(transcript)`, `api.goals.bulk(goals)`

#### T05 — Onboarding must be non-skippable per spec
**Spec change from current:** The spec (Section 2) states "The user cannot skip any step — the Continue button is disabled until a transcript has been received." The Skip button added earlier contradicts this. **Decision required:** keep Skip for UX convenience (current state) or remove per spec. Mark as design decision pending.

---

### P1 — Home Screen Voice Flow

#### T06 — Home mic: record → upload → transcript → suggestions
**File:** `src/pages/HomePage.tsx`
- Replace direct `api.suggestions.request({})` fetch with full voice flow:
  1. Tap mic → start `MediaRecorder`
  2. Tap again → stop → upload → poll transcript
  3. On transcript: call `POST /suggestions` with `{ transcript, void_duration, time_of_day, user_id }`
- Update `api.suggestions.request` payload to accept these fields
- Show "Listening…" → "Tap to finish" → "Thinking…" labels on mic

#### T07 — Home Screen State B (no void pocket)
**File:** `src/pages/HomePage.tsx`
- Detect if current time is inside a fixed block (not free)
- If so: show "Next free window in X minutes" headline, grey out mic (opacity 40%, `pointer-events: none`)
- Show "Check back after [event] ends" label

#### T08 — Home Screen userName from localStorage
**File:** `src/pages/HomePage.tsx`
- Replace hardcoded `'Arjun'` with `localStorage.getItem('userName') ?? 'there'`

---

### P1 — Suggestion Overlay

#### T09 — Suggestion overlay (modal over home screen)
**New file:** `src/components/SuggestionOverlay.tsx` + `.module.css`
- Slide-up from bottom, 300ms spring animation
- Background home screen blurs (`backdrop-filter: blur(8px)`)
- Header: "Here's what I'd suggest" + italic gray transcript snippet
- 3 stacked suggestion cards (with `reason` field from API)
- Auto-dismiss after 30s (no API call on timeout)
- Tap blurred background → same as "Not now"

#### T10 — Overlay card selection + confirm/reject buttons
**File:** `src/components/SuggestionOverlay.tsx`
- Tap card → highlight with solid accent border, others fade to 60% opacity, checkmark icon appears
- "Let's do it" button (AMD red, full width) → `POST /suggestions/accept` with `{ suggestion_id }`
- "Not now" text link → `POST /suggestions/skip` with `{ suggestion_ids: [all three] }`
- On accept: overlay slides down, accepted card moves to top of home cards list with green tint
- Add `api.suggestions.accept(suggestionId)` and `api.suggestions.skip(suggestionIds)` to client

#### T11 — SpeechSynthesis auto-read suggestions in overlay
**File:** `src/components/SuggestionOverlay.tsx`
- After 600ms delay on overlay appear: `speak("Here are three suggestions. One: [title]. Two: [title]. Three: [title].")`
- Highlight each card as its title is spoken
- Use existing `useSpeechOutput` hook

---

### P1 — Global Voice State

#### T12 — Global recording context
**New file:** `src/context/VoiceContext.tsx`
- Single source of truth: `isRecording: boolean`, `activeRecorderId: string | null`
- Ensures only one recording at a time across all screens
- Before starting any new recording: cancel active TTS, stop any existing recording
- Expose via `useVoiceContext()` hook

#### T13 — Global red pulsing dot indicator
**File:** `src/components/AppShell.tsx` (or a portal)
- When `isRecording === true` in VoiceContext: render a fixed `position: fixed; top: 12px; right: 12px` red pulsing dot (`8px` circle, `#ED1C24`, CSS pulse animation)
- Above all screens and above the nav bar (`z-index: 9999`)

#### T14 — Microphone permission denied overlay
**New file:** `src/components/MicPermissionOverlay.tsx`
- Full-screen overlay, cannot be dismissed
- Text: "VoidFill needs mic access to work. Please enable it in your browser settings — then refresh the page."
- "How to enable" link
- Shown when `useVoiceRecorder` returns `error` containing "NotAllowedError" / "denied"
- Must intercept at app level so it appears regardless of which screen triggered the denial

---

### P2 — Goals Screen Completions

#### T15 — Header mic button for multi-goal entry
**File:** `src/pages/GoalsPage.tsx`
- Add mic button to the right of the "Your Goals" heading
- Tap → record → upload → `POST /goals/parse-and-create` with `{ transcript }`
- All matching category cards update simultaneously
- Status: "X goals added!"
- Add `api.goals.parseAndCreate(transcript)` to client

#### T16 — Optimistic UI on goal create
**File:** `src/pages/GoalsPage.tsx`
- On transcript received: immediately insert a placeholder goal item at the top of the target card with a loading/spinning dot
- On API success: replace placeholder with real goal data
- On API failure: remove placeholder, show error

#### T17 — cachedGoals localStorage + offline fallback
**File:** `src/pages/GoalsPage.tsx`
- After successful `GET /goals`: save `goals` array to `localStorage.cachedGoals`
- On mount fetch failure: read from `localStorage.cachedGoals`, show "Showing cached goals — tap to retry" banner
- Tap banner → retry `GET /goals`

#### T18 — CTA card weekly focus: correct endpoint + localStorage save
**File:** `src/pages/GoalsPage.tsx`
- After CTA recording: call `POST /goals/weekly-focus` (not `POST /goals`)
- Save focus string to `localStorage.weeklyFocus`
- Update CTA card display text to show the focus
- Add `api.goals.weeklyFocus(transcript)` to client

---

### P2 — Reflection Screen

#### T19 — Rename route `/suggestions` → `/reflection`
**Files:** `src/App.tsx`, `src/components/AppShell.tsx`, rename `SuggestionsPage.tsx` → `ReflectionPage.tsx`
- Update nav item 3 (Sparkle icon) to link to `/reflection`
- Add redirect or alias so old `/suggestions` doesn't 404

#### T20 — Real reflection API
**File:** `src/pages/ReflectionPage.tsx` (currently SuggestionsPage)
- Replace `GET /goals` + `POST /suggestions/request` with `GET /api/v1/reflection/latest`
- Handle response shape: `{ week_start, week_end, audio_url, summary_text, stats[], priority_next_week }`
- Add `api.reflection.latest()` to client
- Update stat rows to use `reflection.stats` (real `sessions`, `hours`, `neglected`)
- Use `priority_next_week` text in insight card

#### T21 — Reflection empty state
**File:** `src/pages/ReflectionPage.tsx`
- If `GET /reflection/latest` returns 404 or empty: show empty state
- Text: "Your first reflection will be ready after your first week of use."
- "Go to Goals" button → navigate to `/goals`

#### T22 — Real audio playback in reflection
**File:** `src/pages/ReflectionPage.tsx`
- If `audio_url !== null`: create `new Audio(audio_url)`, play on tap, pause on tap again
- If `audio_url === null`: use `useSpeechOutput.speak(summary_text)` on tap, `cancel()` on pause
- Waveform animation tied to actual playback state

#### T23 — "Update Goals for Next Week" recording button
**File:** `src/pages/ReflectionPage.tsx`
- Full-width button at bottom
- Tap → start `MediaRecorder`, button text: "Listening… tap to finish"
- Stop → upload → `POST /goals/parse-and-create`
- On success: TTS says "Got it. I'll use these for next week's suggestions." Button resets.

---

### P2 — Settings Screen Completions

#### T24 — "Your Name" editable row
**File:** `src/pages/SettingsPage.tsx`
- On tap: inline `<input>` appears pre-filled with `localStorage.getItem('userName') ?? 'Arjun'`
- "Done" tap: `localStorage.setItem('userName', value)`, collapse input
- Home screen greeting updates on next visit

#### T25 — Reset Onboarding row
**File:** `src/pages/SettingsPage.tsx`
- Row: "Reset Onboarding" in red text
- Tap → confirmation dialog: "This will clear your routine and goals. Are you sure?"
- Confirm: clear all localStorage keys (`onboardingComplete`, `userName`, `routineTranscript`, `goalsTranscript`, `initialGoals`, `scheduleSkeleton`, `weeklyFocus`, `lastSuggestion`, `cachedGoals`) → navigate to `/onboarding`
- Cancel: close dialog

#### T26 — About VoidFill expandable row
**File:** `src/pages/SettingsPage.tsx`
- Tap → toggle inline expansion showing version (0.1.0) and one-paragraph app description
- Chevron rotates 90° when open

#### T27 — Notification Preferences row (greyed, Coming soon)
**File:** `src/pages/SettingsPage.tsx`
- Toggle row, visually disabled (`opacity: 0.4`)
- Label: "Notifications — Coming soon"
- No interaction

---

### P3 — Error & Offline Handling

#### T28 — Global backend-unreachable banner
**File:** `src/components/AppShell.tsx` (or a global error boundary)
- Non-blocking banner at top of screen: "Can't reach server — some features limited"
- Detect via failed API call (network error / 5xx)
- Auto-dismiss after 4s or on next successful call

#### T29 — 401 session expired handler
**File:** `src/api/client.ts`
- On any 401 response: clear `localStorage.authToken`, show toast "Session ended. Starting fresh.", navigate to `/onboarding`
- Add toast component or integrate into existing status message system

#### T30 — Offline audio queuing
**New file:** `src/utils/offlineQueue.ts`
- On voice upload failure due to network: serialize Blob to base64, store in `localStorage` as `pendingAudio`
- On next app open with connection: auto-retry upload silently
- (Low priority — requires service worker or app-open detection)

---

### P3 — Nav Route Alignment

#### T31 — Remove or repurpose `/voice` and `/schedule` and `/notes` routes
**Spec finding:** The spec's nav bar has exactly 4 icons: Home, Goals, Reflection, Settings. Routes `/voice`, `/schedule`, and `/notes` exist in the current implementation but are not in the spec's nav bar at all.
**Options:**
  - A) Remove them entirely and delete the page files
  - B) Keep them as non-nav utility routes (accessible via deep link only)
  - C) Replace the current nav items with spec-compliant ones — the current nav has Home, Goals, Suggestions(/voice), Settings; the spec has Home, Goals, Reflection, Settings

---

## Summary Counts

| Priority | Count | Status |
|---|---|---|
| Already done (full) | ~60 items | ✅ |
| Already done (partial / spec-deviated) | ~12 items | ⚠️ |
| P0 — Must do (breaks core flow) | 5 tasks (T01–T05) | ❌ |
| P1 — High (core UX, spec-required) | 9 tasks (T06–T14) | ❌ |
| P2 — Medium (per-screen completions) | 13 tasks (T15–T27) | ❌ |
| P3 — Low (error handling, edge cases) | 4 tasks (T28–T31) | ❌ |
| **Total remaining** | **31 tasks** | |

---

## Recommended Build Order

```
Week 1 (Foundation):
  T01 → T03 → T04 → T02   (onboarding full flow with localStorage)
  T08                       (userName from localStorage on home)

Week 2 (Core UX):
  T12 → T13 → T14          (global voice context + indicators + mic denied)
  T06 → T07 → T09 → T10 → T11  (home mic flow + suggestion overlay)

Week 3 (Screen completions):
  T19 → T20 → T21 → T22 → T23  (reflection screen overhaul)
  T15 → T16 → T17 → T18        (goals screen completions)
  T24 → T25 → T26 → T27        (settings completions)

Week 4 (Polish):
  T28 → T29 → T30 → T31        (error handling + route cleanup)
```
