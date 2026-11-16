# Enterprise workflow reconstruction

Browser (React) → FastAPI → SQLite repository → Workflow Orchestrator → bounded specialist stages → evidence-verified update proposal → atomic persistence and version snapshot.

The six runtime roles are Information Filter, Fact Extractor, Project Resolver, Relation Reasoner, Workflow Reconstructor and Evidence Verifier. Local demo analysis uses conservative deterministic extraction. An authorized LLM provider may replace reasoning stages through HelloAgents. Persistence, permissions, job state, review and export remain deterministic services.

Raw messages are immutable and deduplicated by source + message ID. A repeated identical import is idempotent; conflicting content is rejected. Proposals carry references to original quotes. Evidence verification checks source identity and literal containment and guards dangling relations. Review is initially pending. Human acceptance is audited, and training exports contain accepted and verified material only.

Graph versions preserve previous snapshots. Incremental imports rebuild from stored facts so previous work is retained. Retrieval combines lexical similarity, entity hints and project membership; semantic vector infrastructure can be added later and is not required for local operation.

Application binds localhost by default. Optional bearer-token auth protects all APIs when configured, including exports. Restrictive same-origin frontend deployment is preferred. The service has no messaging or enterprise mutation operations.
