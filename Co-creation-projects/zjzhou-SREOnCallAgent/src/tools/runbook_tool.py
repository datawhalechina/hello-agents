import os
import glob
import yaml
from typing import List, Dict, Any


class RunbookLookupTool:
    """
    Fetches runbook remediation procedures by service and error pattern.

    Input to run(): an error pattern keyword (e.g. 'DB pool exhausted', 'Stripe 429')
    Returns: ordered remediation steps from the service's runbook
    """

    name = "runbook_lookup"
    description = (
        "Look up runbook remediation steps for a service and error pattern. "
        "Input: an error pattern keyword (e.g. 'DB pool exhausted', 'Stripe API 429', 'memory leak'). "
        "Returns ordered remediation steps from the on-call runbook."
    )

    def __init__(self, service: str, runbooks_dir: str):
        self.service = service
        self.runbooks_dir = runbooks_dir

    def _load_runbook(self) -> Dict[str, Any]:
        path = os.path.join(self.runbooks_dir, f"{self.service}.yaml")
        if os.path.exists(path):
            with open(path) as f:
                return yaml.safe_load(f) or {}
        # Fallback: search all runbooks
        for rb_path in glob.glob(os.path.join(self.runbooks_dir, "*.yaml")):
            with open(rb_path) as f:
                data = yaml.safe_load(f) or {}
            if data.get("service", "") in self.service or self.service in data.get("service", ""):
                return data
        return {}

    def run(self, error_pattern: str) -> str:
        runbook = self._load_runbook()
        if not runbook:
            return f"No runbook found for service '{self.service}'."

        query = error_pattern.lower()
        procedures: List[Dict] = runbook.get("procedures", [])

        matching = [p for p in procedures if query in p.get("pattern", "").lower()]
        if not matching:
            matching = procedures  # Return all if no specific match

        if not matching:
            return f"No runbook procedures found for pattern '{error_pattern}'."

        lines = [
            f"Runbook: {runbook.get('service', 'unknown')} "
            f"(v{runbook.get('runbook_version', '?')})"
        ]
        for proc in matching:
            lines.append(
                f"\nPattern: '{proc['pattern']}' | Severity: {proc.get('severity', 'unknown')}"
            )
            lines.append("Remediation steps:")
            for i, step in enumerate(proc.get("steps", []), 1):
                lines.append(f"  {i}. {step}")
        return "\n".join(lines)
