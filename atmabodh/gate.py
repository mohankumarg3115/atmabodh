"""The Privacy Gate: every data access passes through here.

Two jobs:
1. Consent - the user can switch each source (body / usage / calendar)
   on or off. If a source is off, the gate refuses and returns None.
2. Audit log - every request is written down: time, source, tool,
   the reason, and whether it was allowed. The log never stores the
   data itself, only the fact that it was accessed.

This is what the MCP servers sit behind. In the app, the user sees this
log in plain language ("Read your sleep summary at 12:05 AM, reason:
bedtime check").
"""
import datetime as dt
import json

from atmabodh import config


class PrivacyGate:
    def __init__(self, consent_path=None, audit_path=None):
        config.ensure_home()
        self.consent_path = consent_path or config.CONSENT_PATH
        self.audit_path = audit_path or config.AUDIT_PATH

    # ---- consent -------------------------------------------------------
    def consent(self) -> dict:
        try:
            saved = json.loads(self.consent_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            saved = {}
        return {s: bool(saved.get(s, True)) for s in config.SOURCES}

    def set_consent(self, source: str, allowed: bool):
        if source not in config.SOURCES:
            raise ValueError(f"Unknown source: {source}")
        c = self.consent()
        c[source] = bool(allowed)
        self.consent_path.write_text(json.dumps(c, indent=2))

    # ---- access ----------------------------------------------------------
    def call(self, source: str, tool, reason: str, **kwargs):
        """Run `tool(**kwargs)` only if `source` is allowed. Always log it."""
        allowed = self.consent().get(source, False)
        self._log(source, tool.__name__, reason, allowed)
        return tool(**kwargs) if allowed else None

    def _log(self, source, tool_name, reason, allowed):
        entry = {"time": dt.datetime.now().isoformat(timespec="seconds"),
                 "source": source, "tool": tool_name, "reason": reason, "allowed": allowed}
        with open(self.audit_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def read_log(self, last: int = 50) -> list[dict]:
        try:
            lines = self.audit_path.read_text().strip().splitlines()
        except FileNotFoundError:
            return []
        return [json.loads(l) for l in lines[-last:]]
