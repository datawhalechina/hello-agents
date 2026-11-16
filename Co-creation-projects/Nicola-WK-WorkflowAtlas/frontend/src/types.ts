export type FactKind = 'task' | 'event' | 'decision' | 'issue' | 'artifact' | 'plan'
export type ReviewStatus = 'pending' | 'accepted' | 'rejected'
export interface Evidence { message_id: string; source_id: string; quote: string }
export interface Message { id: string; source_id: string; source_type: string; chat_id: string; sender: string; text: string; timestamp: string; thread_id?: string | null; metadata: Record<string, unknown> }
export interface Fact { id: string; kind: FactKind; summary: string; project_hint: string | null; project_id: string | null; entity_key: string | null; actor: string | null; status: string; occurred_at: string; evidence: Evidence[]; confidence: number; verified: boolean; review_status: ReviewStatus; attributes: Record<string, unknown> }
export interface Project { source_id?: string | null; analysis_mode?: 'local' | 'model'; id: string; name: string; description: string; status: string; aliases: string[]; created_at: string }
export interface WorkflowNode { id: string; project_id: string; kind: FactKind; label: string; status: string; fact_ids: string[]; evidence: Evidence[]; occurred_at: string; verified: boolean }
export interface WorkflowEdge { id: string; project_id: string; source: string; target: string; relation: string; evidence: Evidence[]; confidence: number; verified: boolean; rationale: string }
export interface Workflow { project: Project; nodes: WorkflowNode[]; edges: WorkflowEdge[]; facts: Fact[]; version: number; warnings: string[]; related_nodes?: WorkflowNode[]; related_edges?: WorkflowEdge[]; related_facts?: Fact[] }
export interface Stats { messages: number; facts: number; projects: number; nodes: number; edges: number; pending_review: number; versions: number }
export interface Source { id: string; type: string; message_count: number; last_timestamp: string }
export interface Stage { agent: string; status: 'completed' | 'failed' | 'skipped'; input_count: number; output_count: number; detail: string; duration_ms: number }
export interface Runtime { provider: string; framework: string; agents: string[]; limitations: string[]; agent_results?: Stage[] }
export interface Version { version: number; created_at: string }
export interface Job { purpose?: 'answer' | 'diagram' | 'facts'; id: string; status: string; error: string | null; source_id?: string | null; cancel_requested?: boolean; progress?: { total_messages?: number; processed_messages?: number; cached_messages?: number; batch_index?: number; total_batches?: number; stage?: string; markdown?: string; usage?: Record<string, number>; model?: string; thinking?: boolean; thinking_controlled?: boolean; finish_reason?: string | null; elapsed_ms?: number }; result: { facts?: number; projects?: number; warnings?: string[]; complete?: boolean } | null }
export interface ModelSettings { provider: 'local-demo' | 'helloagents-llm'; model: string; base_url: string; api_key_configured: boolean; external_data_authorized: boolean; batch_size: number; thinking: boolean; saved: boolean; test_status: 'not_tested' | 'passed'; storage_error: string | null }
export interface ModelConnectionResult { ok: boolean; detail: string; latency_ms: number }
export interface ModelWorkstream { id: string; name: string; owners: string[]; status: string; summary: string; evidence: Evidence[] }
export interface ModelWorkflowStep { id: string; workstream_id: string | null; title: string; kind: FactKind; actor: string | null; status: string; occurred_at: string | null; evidence: Evidence[] }
export interface ModelWorkflowRelation { source_step_id: string; target_step_id: string; relation: string; rationale: string; evidence: Evidence[] }
export interface ModelReportTable { title: string; columns: string[]; rows: { cells: string[]; evidence: Evidence[] }[] }
export interface ModelWorkflowReport { summary: string; workstreams: ModelWorkstream[]; steps: ModelWorkflowStep[]; relations: ModelWorkflowRelation[]; tables: ModelReportTable[]; uncertainties: string[]; limitations: string[] }
export interface DirectModelAnswer { markdown: string; complete: boolean; finish_reason: string | null; usage: Record<string, number>; model: string; thinking: boolean; thinking_controlled?: boolean; elapsed_ms: number }
export interface ModelReportView { source_id: string; report: ModelWorkflowReport | DirectModelAnswer | null; version: number | null; created_at: string | null; stale: boolean; format?: string; cached?: boolean; diagram?: DirectModelAnswer | null; diagram_stale?: boolean; diagram_cached?: boolean; fact_graph?: { version: number; cached: boolean; stale: boolean } | null }
export interface ImportReport { imported: number; duplicates: number; source_id: string; warnings: string[] }
export interface ImportIssue { position: number; line?: number | null; field: string; code: string; detail: string; raw: unknown }
export type ImportFormat = 'auto' | 'json' | 'jsonl' | 'csv' | 'txt' | 'html'
export interface ImportPreview { fingerprint: string; source_id: string; format_detected: ImportFormat; total: number; valid: number; imported_candidates: number; duplicates: number; issues: ImportIssue[]; messages: Message[]; warnings: string[] }
export interface Audit { fact_id: string; created_at: string; status: ReviewStatus; reviewer: string; note: string }
export interface SourceDeletionPreview { source_id: string; messages: number; facts: number; projects_removed: number; reviews: number; versions: number; checkpoint: boolean; jobs_reset: number; version: number }
export interface SourceDeletionResult { source_id: string; messages_deleted: number; facts_deleted: number; projects_removed: number; reviews_deleted: number; versions_updated: number; jobs_reset: number; remaining_sources: number; version: number }
export interface SourceAnalysis { source_id: string; messages: number; message_types: Record<string, number>; textual_messages: number; attachment_messages: number; reply_messages: number; extracted_messages: number; facts: number; assigned_facts: number; unassigned_facts: number; verified_facts: number; pending_review: number; projects: number; nodes: number; explicit_edges: number; attribution_methods: Record<string, number>; notes: string[] }
