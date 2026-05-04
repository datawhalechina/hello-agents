from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DATA_ROOT = ROOT.parents[1] / "data" / "rss_digest"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rss_digest.pipeline import run_pipeline
from rss_digest.ui_server import serve_ui


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run_pipeline(ROOT, DATA_ROOT)
    else:
        serve_ui(ROOT, DATA_ROOT)
