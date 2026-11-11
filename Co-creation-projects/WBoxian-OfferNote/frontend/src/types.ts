export type Mode = 'demo' | 'live'
export type Verdict = 'supported' | 'partial' | 'unverified'
export type Page = 'overview' | 'materials' | 'interview' | 'review' | 'activity' | 'settings'
export interface Requirement {
  priority?: 'high' | 'medium' | 'low'
  preparation_action?: string
  id: string
  title: string
  topic: string
  requirement_quote: string
  evidence_quote: string
  status: 'supported' | 'partial' | 'missing' | 'needs_review'
  reason: string
  requirement_verified: boolean
  evidence_verified: boolean
}
export interface Claim {
  id: string
  text: string
  quote: string
  topic: string
  risk: string
  confirmed: boolean
  quote_verified: boolean
}
export interface Analysis {
  id: string
  summary: string
  mode: Mode
  created_at: string
  requirements: Requirement[]
  claims: Claim[]
  warnings: string[]
}
export interface Question {
  id: string
  text: string
  source_quote: string
  topic: string
  intent: string
  criteria: string[]
  follow_up_depth: number
}
export interface Feedback {
  verdict: Verdict
  strengths: string[]
  gaps: string[]
  answer_quotes: string[]
  next_step: string
  follow_up: string
  quotes_verified: boolean
}
export interface Turn {
  id?: string
  request_id: string
  question: Question
  answer: string
  answer_source?: string
  feedback?: Feedback
  created_at: string
}
export interface ReferenceAnswer {
  turn_id: string
  answer: string
  key_points: string[]
  pitfalls: string[]
}
export interface Report {
  reference_answers?: ReferenceAnswer[]
  reference_answers_error?: string | null
  summary?: string
  total_score?: number | null
  covered_weight?: number
  rubric_version?: string
  scores?: DimensionScore[]
  topics?: { topic_id: string; score: number | null; reason: string; evidence: EvidenceRef[] }[]
  strengths?: Finding[]
  weaknesses?: Finding[]
  improvements?: Improvement[]
  warnings?: string[]
  answered: number
  planned: number
  groups: Record<Verdict, string[]>
  actions: string[]
  weak_topics: string[]
  scope: string
  demo_notice: string
}
export interface Session {
  demonstration?: boolean
  workflow_version?: number
  budget?: { total_turns: number; max_topic_turns: number }
  topics?: InterviewTopic[]
  current_topic_id?: string
  trace?: DecisionTrace[]
  report_error?: string | null
  end_reason?: string
  id: string
  mode: Mode
  focus: 'all' | 'weak'
  status: 'active' | 'awaiting_report' | 'completed'
  questions: Question[]
  turns: Turn[]
  report: Report | null
  created_at: string
  analysis_id: string
}
export interface Workspace {
  demo_role?: string | null
  id: string
  name: string
  role: string
  resume: string
  job: string
  analysis: Analysis | null
  sessions: Session[]
  revision: number
  updated_at: string
}
export interface WorkspaceSummary {
  demo_role?: string | null
  id: string
  name: string
  role: string
  updated_at: string
  session_count: number
  has_analysis: boolean
}
export interface Settings {
  base_url: string
  max_tokens: number
  protocol: string
  api_key_configured: boolean
  configured: boolean
  model: string
  adapter: string
  default_mode: string
}
export interface RunEvent {
  name?: string
  id: string
  created_at: string
  stage: string
  mode: Mode
  model: string
  duration_ms: number
  status: string
  input_chars: number
  tokens: null | number
  input_tokens?: number | null
  output_tokens?: number | null
  usage_complete?: boolean
  repairs?: number
  finish_reason?: string | null
}

export interface EvidenceRef {
  turn_id: string
  quote: string
}
export interface Finding {
  text: string
  evidence: EvidenceRef[]
}
export interface Improvement {
  topic_id: string
  priority: 'high' | 'medium' | 'low'
  title: string
  detail: string
  exercise: string
  evidence: EvidenceRef[]
}
export interface DimensionScore {
  dimension: string
  label: string
  weight: number
  score: number | null
  reason: string
  evidence: EvidenceRef[]
}
export interface InterviewTopic {
  id: string
  title: string
  status: 'unvisited' | 'active' | 'closed'
  covered: string[]
  gaps: string[]
  contradictions: string[]
  closure: string | null
  reason: string
}
export interface DecisionTrace {
  action: 'ask_followup' | 'switch_topic' | 'finish'
  topic_id: string
  reason: string
  closure: string | null
  created_at: string
  tools: { id: string; name: string; topic_id?: string; status: string; duration_ms: number }[]
}
