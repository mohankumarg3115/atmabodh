"""Shared settings: where local files live and the tuning knobs.

Everything is stored in the local `.atmabodh/` folder. Nothing is sent
anywhere. On the phone this becomes the app's private storage
(Room + SQLCipher); in this laptop prototype it is plain SQLite + JSON.
"""
from pathlib import Path
import os

HOME = Path(os.environ.get("ATMABODH_HOME", Path(__file__).resolve().parent.parent / ".atmabodh"))
DB_PATH = HOME / "local_store.sqlite"     # all personal data (daily aggregates)
CONSENT_PATH = HOME / "consent.json"      # which data sources the user allows
AUDIT_PATH = HOME / "access_log.jsonl"    # every data access: who, what, why
NUDGE_LOG_PATH = HOME / "nudges.jsonl"    # nudges sent (for the daily cap)

# Data sources the user can switch on/off (one MCP server each)
SOURCES = ("body", "usage", "calendar")

# Personal model
COLD_START_DAYS = 14          # before this many labelled days we use rules
RIDGE_ALPHA = 1.0             # strength of Ridge's "safety brake"
USUAL_SLEEP_H = 7.5           # fallback sleep need before we learn the user's own

# Nudge rules
LATE_NIGHT_FROM_H = 23.5      # 11:30 PM
LATE_BEDTIME_H = 24.5         # bedtime after 12:30 AM counts as a "late night"
DISTRACTING = {"social", "video", "games"}
MIN_SESSION_MIN = 20
EVENT_WINDOW_H = 14           # "big event tomorrow" = important event within 14 h
MAX_NUDGES_PER_DAY = 2

# Optional local LLM (Ollama) used only to word the nudge.
# On the phone this is Gemma 4 E2B on LiteRT-LM.
LLM_URL = os.environ.get("ATMABODH_LLM_URL", "http://localhost:11434/api/generate")
LLM_MODEL = os.environ.get("ATMABODH_LLM_MODEL", "gemma3:1b")


def ensure_home():
    HOME.mkdir(parents=True, exist_ok=True)
