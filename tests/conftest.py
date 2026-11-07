import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Tests must never call the real API, whatever the developer's shell has set.
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("ACCESS_CODES", None)
os.environ["TK_NO_DOTENV"] = "1"  # ignore a developer's local .env
