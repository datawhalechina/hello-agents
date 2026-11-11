# -*- coding: utf-8 -*-
"""Journal impact-factor lookup backed by a local metrics table.

Problem Solved:
    PubMed E-utilities does not return journal impact factors, so an
    impact-factor filter needs an external data source. JCR (Clarivate)
    has no free official API, therefore this service loads a local,
    user-extendable JSON table (data/journal_metrics.json) keyed by the
    PubMed journal abbreviation (normalized: lowercase, no dots).

Design Notes:
    - The table ships with ~68 common oncology/biomedical journals as a
      starting point; users can extend it for their own field.
    - Journals missing from the table yield ``None`` so callers can decide
      how to treat them (filter out or keep).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "journal_metrics.json"

# Common journal name variants -> normalized key (lowercase, no dots)
_VARIANT_REPLACEMENTS = [
    (re.compile(r"\bthe\b"), ""),
]


_STOP_WORDS = {
    "of", "and", "the", "et", "de", "del", "for", "in", "on", "a", "an",
}


class JournalMetrics:
    """Load and query the journal impact-factor table."""

    def __init__(self, data_path: Optional[Path] = None) -> None:
        self.data_path = Path(data_path) if data_path else _DEFAULT_DATA_PATH
        self._table: dict[str, float] = {}
        self._table_acronym: dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        if not self.data_path.exists():
            logger.warning(
                "Journal metrics table not found at %s; impact factors disabled",
                self.data_path,
            )
            return
        try:
            raw = json.loads(self.data_path.read_text(encoding="utf-8"))
            for key, value in (raw.get("journals") or {}).items():
                jif = float(value)
                self._table[self._normalize(key)] = jif
                acronym = self._acronym(key)
                if len(acronym) >= 2:
                    self._table_acronym.setdefault(acronym, jif)
            logger.info(
                "Journal metrics loaded: %d journals from %s",
                len(self._table),
                self.data_path,
            )
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning("Failed to load journal metrics: %s", exc)
            self._table = {}

    def impact_factor(self, journal: str) -> Optional[float]:
        """Return the impact factor for a journal name, or None if unknown.

        Matching is two-step: an exact normalized match first, then an
        acronym match so full journal names (e.g. "British Journal of
        Cancer") resolve against abbreviated table keys ("Br J Cancer").
        """
        if not journal:
            return None
        key = self._normalize(journal)
        jif = self._table.get(key)
        if jif is not None:
            return jif
        acronym = self._acronym(journal)
        if len(acronym) < 2:
            return None
        return self._table_acronym.get(acronym)

    def is_known(self, journal: str) -> bool:
        """Return True when the journal has an impact factor in the table."""
        return self.impact_factor(journal) is not None

    @staticmethod
    def _normalize(name: str) -> str:
        """Normalize a journal name for lookup: lowercase, strip dots."""
        value = name.lower()
        value = re.sub(r"\.[a-z]", lambda m: m.group(0)[1], value)  # "Br. J. Cancer" -> "br j cancer"
        value = re.sub(r"[^a-z0-9]+", " ", value).strip()
        value = re.sub(r"^the\s+", "", value)  # "The oncologist" -> "oncologist"
        return value

    @staticmethod
    def _acronym(name: str) -> str:
        """Build the initial-letter acronym, skipping common stop words."""
        words = re.findall(r"[a-z0-9]+", name.lower())
        return "".join(
            word[0] for word in words if word not in _STOP_WORDS
        )
