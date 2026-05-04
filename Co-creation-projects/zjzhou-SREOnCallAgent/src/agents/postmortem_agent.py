import json
from typing import Dict, Any

from src.core.llm_client import HelloAgentsLLM

DRAFT_PROMPT = """
You are a senior SRE writing a post-mortem report for a production incident.
Write a clear, structured post-mortem in Markdown using the incident data and investigation
findings provided below.

INCIDENT DATA:
{incident_json}

INVESTIGATION FINDINGS:
Root Cause: {root_cause}

Evidence Collected:
{evidence}

Runbook Consulted:
{runbook}

Write the post-mortem with these EXACT sections:
1. ## Executive Summary (2-3 sentences: what happened, impact, resolution)
2. ## Incident Timeline (bullet list of timestamped events from the logs)
3. ## Root Cause Analysis (5-Whys: start with the symptom and ask 'why?' 5 times)
4. ## Impact Assessment (severity, affected users, duration estimate, business impact)
5. ## Immediate Remediation Steps (numbered list of actions to take RIGHT NOW)
6. ## Action Items (table with columns: Action | Owner | Due Date | Priority)
7. ## Lessons Learned (2-4 bullet points about what this incident taught us)

Be specific — reference actual log messages, metric values, and timestamps from the data.
"""

CRITIQUE_PROMPT = """
You are a post-mortem review board member. Critically evaluate the draft post-mortem below
against these quality criteria:

1. ROOT CAUSE: Is the root cause clearly and specifically stated (not vague)?
2. TIMELINE: Are all key events from the logs included with accurate timestamps?
3. ACTION ITEMS: Are they specific, measurable, and assigned with due dates?
4. 5-WHYS: Does it reach the true systemic root cause (not stop at symptoms)?
5. LESSONS LEARNED: Are they actionable (not generic platitudes)?

Draft Post-Mortem:
{draft}

Respond with a JSON object:
{{
  "score": <1-10>,
  "issues": ["<issue 1>", "<issue 2>", ...],
  "suggestions": ["<improvement 1>", "<improvement 2>", ...]
}}
"""

REVISE_PROMPT = """
Revise the post-mortem draft below to address the reviewer's feedback.
Apply ALL suggestions and fix ALL identified issues.

ORIGINAL DRAFT:
{draft}

REVIEWER FEEDBACK:
{critique}

Output the complete revised post-mortem in Markdown. No preamble — start directly with
the post-mortem content.
"""


class PostmortemAgent:
    """
    Reflection agent: draft → critique → revise post-mortem report.

    This is the third stage of the pipeline. It uses the Reflection pattern:
    first drafting an RCA report, then self-critiquing it against quality criteria,
    then producing a final revised version.
    """

    def __init__(self, llm: HelloAgentsLLM, max_revisions: int = 1):
        self.llm = llm
        self.max_revisions = max_revisions

    def run(self, incident: Dict[str, Any], findings: Dict[str, Any]) -> str:
        print("\n" + "=" * 60)
        print("📝 STAGE 3: POST-MORTEM — Reflection (draft → critique → revise)")
        print("=" * 60)

        evidence_text = "\n\n".join(
            f"[{e['tool']}({e['query']})]:\n{e['result']}"
            for e in findings.get("evidence", [])
        ) or "No structured evidence collected."

        runbook_text = "\n\n".join(findings.get("runbook_steps", [])) or "No runbook consulted."

        draft = self._draft(incident, findings, evidence_text, runbook_text)
        print("\n✍️  Draft post-mortem written.")

        for revision in range(1, self.max_revisions + 1):
            critique = self._critique(draft)
            print(f"\n🔍 Critique (revision {revision}):\n{critique[:500]}...")
            score = self._extract_score(critique)
            print(f"   Quality score: {score}/10")

            if score >= 8:
                print("✅ Quality threshold met — no revision needed.")
                break

            print(f"   Revising post-mortem (score {score} < 8)...")
            draft = self._revise(draft, critique)
            print(f"   Revision {revision} complete.")

        print("\n✅ Final post-mortem ready.")
        return draft

    def _draft(
        self,
        incident: Dict[str, Any],
        findings: Dict[str, Any],
        evidence_text: str,
        runbook_text: str,
    ) -> str:
        incident_json = json.dumps(
            {
                "incident_id": incident["incident_id"],
                "service": incident["service"],
                "severity": incident["severity"],
                "alert": incident["alert"],
                "affected_users": incident.get("affected_users", 0),
            },
            indent=2,
        )
        prompt = DRAFT_PROMPT.format(
            incident_json=incident_json,
            root_cause=findings.get("root_cause", "Unknown"),
            evidence=evidence_text,
            runbook=runbook_text,
        )
        messages = [{"role": "user", "content": prompt}]
        return self.llm.think(messages=messages)

    def _critique(self, draft: str) -> str:
        prompt = CRITIQUE_PROMPT.format(draft=draft)
        messages = [{"role": "user", "content": prompt}]
        return self.llm.think(messages=messages)

    def _revise(self, draft: str, critique: str) -> str:
        prompt = REVISE_PROMPT.format(draft=draft, critique=critique)
        messages = [{"role": "user", "content": prompt}]
        return self.llm.think(messages=messages)

    def _extract_score(self, critique: str) -> int:
        import re
        match = re.search(r'"score"\s*:\s*(\d+)', critique)
        return int(match.group(1)) if match else 7
