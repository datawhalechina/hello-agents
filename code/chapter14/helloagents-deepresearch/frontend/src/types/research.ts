export interface SourceItem {
  title: string;
  url: string;
  snippet: string;
  raw: string;
}

export interface ToolCallLog {
  eventId: number;
  agent: string;
  tool: string;
  parameters: Record<string, unknown>;
  result: string;
  noteId: string | null;
  notePath: string | null;
  timestamp: number;
}

export interface TodoTaskView {
  id: number;
  title: string;
  intent: string;
  query: string;
  status: string;
  summary: string;
  sourcesSummary: string;
  sourceItems: SourceItem[];
  notices: string[];
  noteId: string | null;
  notePath: string | null;
  toolCalls: ToolCallLog[];
}

export interface JobItemView {
  id: string;
  company: string;
  title: string;
  location: string;
  sourceUrl: string;
  sourceTitle: string;
  requirements: string[];
  responsibilities: string[];
  techStack: string[];
  duration: string;
  deadline: string;
  matchScore: number | null;
  matchReason: string;
  resumeAdvice: string[];
  risks: string[];
  applicationStatus: string | null;
  statusNote: string;
  savedAt: string;
  updatedAt: string;
}

export interface SearchDiagnosticsView {
  taskId: number;
  taskTitle: string;
  backend: string;
  query: string;
  finalQuery: string;
  retryQuery: string | null;
  counts: {
    raw: number;
    reliable: number;
    filtered: number;
  };
  rejectReasons: Record<string, number>;
  rejectedSamples: Array<{
    title: string;
    url: string;
    reason: string;
  }>;
  suggestion: string;
}

export type StreamStatus =
  | "idle"
  | "running"
  | "retrying"
  | "interrupted"
  | "completed"
  | "error"
  | "cancelled";

export interface InternshipExample {
  label: string;
  form: Partial<ResearchFormState>;
}

export interface ResearchFormState {
  topic: string;
  searchApi: string;
  targetRole: string;
  cities: string;
  season: string;
  availability: string;
  skills: string;
  projectHighlights: string;
  companyPreference: string;
  extraNotes: string;
}
