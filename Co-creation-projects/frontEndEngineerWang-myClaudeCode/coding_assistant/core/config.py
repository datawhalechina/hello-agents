"""Process configuration and terminal I/O."""

import os
import threading
from pathlib import Path

try:
    import readline
    readline.parse_and_bind('set bind-tty-special-chars off')
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]
PRIMARY_MODEL = MODEL
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL_ID")

_PERMISSION_MODE_ALIASES = {
    "1": "request",
    "ask": "request",
    "request": "request",
    "request_approval": "request",
    "2": "full",
    "allow": "full",
    "full": "full",
    "full_approval": "full",
}
_permission_mode_value = os.getenv("PERMISSION_MODE", "request").strip().lower()
if _permission_mode_value not in _PERMISSION_MODE_ALIASES:
    allowed = "request or full"
    raise ValueError(
        f"Invalid PERMISSION_MODE={_permission_mode_value!r}; expected {allowed}"
    )
PERMISSION_MODE = _PERMISSION_MODE_ALIASES[_permission_mode_value]

SKILLS_DIR = WORKDIR / "skills"
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
TOOL_RESULTS_DIR = WORKDIR / ".task_outputs" / "tool-results"
TOKEN_USAGE_DIR = WORKDIR / ".token_usage"

DEFAULT_MAX_TOKENS = 8000
ESCALATED_MAX_TOKENS = 16000
MAX_RETRIES = 3
MAX_CONSECUTIVE_529 = 2
MAX_RECOVERY_RETRIES = 2
BASE_DELAY_MS = 500
# Context budget in estimated chars (json.dumps length of the message list).
# 50k fired compaction after a handful of file reads, wiping tool results the
# agent still needed and forcing a read -> compact -> re-read loop. 120k chars
# is roughly 30-50k tokens: enough headroom for a working set of files while
# still compacting long before the model's real window fills. Override with
# the CONTEXT_LIMIT env var.
CONTEXT_LIMIT = int(os.getenv("CONTEXT_LIMIT", "120000"))
KEEP_RECENT_TOOL_RESULTS = int(os.getenv("KEEP_RECENT_TOOL_RESULTS", "3"))
CONTEXT_ACTIVE_THRESHOLD = float(os.getenv("CONTEXT_ACTIVE_THRESHOLD", "0.70"))
CONTEXT_COMPACT_THRESHOLD = float(os.getenv("CONTEXT_COMPACT_THRESHOLD", "0.85"))
CONTEXT_SUMMARY_THRESHOLD = float(os.getenv("CONTEXT_SUMMARY_THRESHOLD", "0.95"))
PROMPT_CACHE_ENABLED = os.getenv("PROMPT_CACHE_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}
PROMPT_CACHE_TTL = os.getenv("PROMPT_CACHE_TTL", "5m").strip()
TRACE_FULL_PAYLOAD = os.getenv("TRACE_FULL_PAYLOAD", "false").strip().lower() in {"1", "true", "yes", "on"}
INPUT_COST_PER_MILLION = float(os.getenv("INPUT_COST_PER_MILLION", "0"))
CACHE_READ_COST_MULTIPLIER = float(os.getenv("CACHE_READ_COST_MULTIPLIER", "0.1"))
if not (0 < CONTEXT_ACTIVE_THRESHOLD <= CONTEXT_COMPACT_THRESHOLD
        <= CONTEXT_SUMMARY_THRESHOLD <= 1):
    raise ValueError("Context thresholds must satisfy 0 < active <= compact <= summary <= 1")
PERSIST_THRESHOLD = 30000
CONTINUATION_PROMPT = "Continue from the previous response. Do not repeat completed work."
PROMPT = "\033[36ms15 >> \033[0m"
CLI_ACTIVE = False


class ConsoleBroker:
    """Serialize normal prompts and worker permission questions on one stdin."""

    def __init__(self):
        self._lock = threading.Lock()
        self.reader = None

    def ask(self, prompt: str) -> str:
        with self._lock:
            return (self.reader or input)(prompt)


CONSOLE = ConsoleBroker()


def terminal_print(text: str):
    if threading.current_thread() is threading.main_thread() or not CLI_ACTIVE:
        print(text)
        return
    line = ""
    if READLINE_AVAILABLE:
        try:
            line = readline.get_line_buffer()
        except Exception:
            line = ""
    print(f"\r\033[K{text}")
    print(PROMPT + line, end="", flush=True)
