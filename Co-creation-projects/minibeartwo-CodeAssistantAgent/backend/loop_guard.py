"""Detect repeated annotation actions without counting legitimate new evidence."""
from __future__ import annotations

import hashlib
import json
from collections import Counter


class AnnotationLoopGuard:
    def __init__(self):
        self.repeats = Counter()
        self.idle_steps = 0

    def observe(self, name: str, args: dict, before: str, after: str) -> str | None:
        # Only actual new read coverage, a changed hash or a checked/applied file
        # advances the token. Different summaries and search queries do not.
        if before != after:
            self.repeats.clear()
            self.idle_steps = 0
            return None
        signature = hashlib.sha256(json.dumps(
            [name, args], sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        self.repeats[signature] += 1
        self.idle_steps += 1
        if self.repeats[signature] >= 6 or self.idle_steps >= 12:
            return "pause"
        if self.repeats[signature] == 3 or self.idle_steps == 6:
            return "warning"
        return None
