/** All API types mirroring backend Pydantic schemas */

export type UUID = string;

// ── Voice ──────────────────────────────────────────────────────────────────
export type VoiceJobStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface VoiceUploadResponse {
  job_id: UUID;
  status: VoiceJobStatus;
}

export interface VoiceResultResponse {
  job_id: UUID;
  status: VoiceJobStatus;
  transcript: string | null;
  created_at: string;
  updated_at: string;
}

export interface VoiceIntelligenceResponse {
  id: UUID;
  job_id: UUID;
  intent: string;
  extracted_text: string;
  matched_goal_id: UUID | null;
  created_at: string;
}

// ── Goals ──────────────────────────────────────────────────────────────────
export interface Goal {
  id: UUID;
  user_id: UUID;
  title: string;
  description: string | null;
  priority: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface GoalCreate {
  title: string;
  description?: string;
  priority?: number;
}

export interface GoalListResponse {
  goals: Goal[];
  count: number;
}

export interface GoalSearchResult {
  goal: Goal;
  similarity: number;
}

// ── Suggestions ────────────────────────────────────────────────────────────
export interface Suggestion {
  id: UUID;
  user_id: UUID;
  goal_id: UUID | null;
  text: string;
  score: number;
  estimated_minutes: number | null;
  accepted: boolean;
  created_at: string;
}

export interface SuggestionListResponse {
  suggestions: Suggestion[];
  count: number;
}

export interface SuggestionRequest {
  goal_id?: UUID;
  context?: string;
}

export interface SuggestionAcceptRequest {
  suggestion_id: UUID;
}

export interface SuggestionSkipRequest {
  suggestion_ids: UUID[];
}

export interface SuggestionAcceptResponse {
  status: string;
}

export interface SuggestionSkipResponse {
  status: string;
}

// ── Notes ──────────────────────────────────────────────────────────────────
export interface Note {
  id: UUID;
  user_id: UUID;
  content: string;
  source_job_id: UUID | null;
  created_at: string;
}

export interface NoteListResponse {
  notes: Note[];
  count: number;
}

// ── Schedule ───────────────────────────────────────────────────────────────
export interface ScheduleBlock {
  id: UUID;
  user_id: UUID;
  block_type: string;
  start_time: string;
  end_time: string;
  created_at: string;
}

export interface ScheduleBlockCreate {
  block_type: string;
  start_time: string;
  end_time: string;
}

export interface ScheduleBlockListResponse {
  blocks: ScheduleBlock[];
  count: number;
}

// ── Void Intelligence Engine (Phase 8) ─────────────────────────────────────
export interface VoidSlotResponse {
  start_time: string;
  end_time: string;
  duration_minutes: number;
}

export interface VoidSuggestion {
  id?: UUID;
  goal_id: UUID | null;
  title: string;
  score: number;
  reason?: string;
}

export interface VoidNowResponse {
  status: 'void' | 'scheduled';
  current_block: ScheduleBlock | null;
  void_slot: VoidSlotResponse | null;
  suggestions: VoidSuggestion[];
}

// ── Void AI Planner (Phase 9) ───────────────────────────────────────────────
export interface VoidPlanResponse {
  status: string;
  void_minutes: number | null;
  recommended_goal: string | null;
  recommended_action: string | null;
  confidence: number | null;
  reason: string | null;
}

// ── Autonomy Engine (Phase 15) ──────────────────────────────────────────────
export interface AutonomyResponse {
  status: 'scheduled' | 'skipped';
  reason: string;
  block_id: UUID | null;
  void_minutes: number;
  suggestion_title: string | null;
}

export interface AutonomyLogEntry {
  id: string;
  title: string;
  scheduled_at: string;
  duration_minutes: number;
  category: string;
  confidence?: number;
  reason?: string;
  block_id?: string | null;
}

// ── Habit Engine (Phase 13/14) ──────────────────────────────────────────────
export interface HabitSummaryItem {
  goal_title: string;
  sessions: number;
  total_minutes: number;
  habit_strength: number;
}

export interface TimePatternItem {
  hour: number;
  sessions: number;
}

export interface HabitSummaryResponse {
  top_habits: HabitSummaryItem[];
  time_patterns: TimePatternItem[];
  avg_session_minutes: number;
}

// ── Memory Engine (Phase 11/12) ─────────────────────────────────────────────
export interface MemoryGoalSummary {
  goal_id: UUID | null;
  title: string;
  sessions: number;
  total_minutes: number;
}

export interface MemoryActionSummary {
  title: string;
  minutes: number;
  created_at: string;
}

export interface MemorySummaryResponse {
  top_goals: MemoryGoalSummary[];
  recent_actions: MemoryActionSummary[];
}

export interface MemoryRecordRequest {
  goal_id?: UUID;
  title: string;
  minutes: number;
}

// ── Goal parse-and-create ──────────────────────────────────────────────────
export interface GoalParseAndCreateResponse {
  goals: Goal[];
}
export interface WeeklyFocusResponse {
  focus: string;
}
// ── Reflection ──────────────────────────────────────────────────────────────
export interface ReflectionStat {
  category: string;
  sessions: number;
  hours: number;
  neglected: boolean;
}

export interface ReflectionResponse {
  week_start: string;
  week_end: string;
  audio_url: string | null;
  summary_text: string | null;
  stats: ReflectionStat[];
  priority_next_week: string | null;
}
