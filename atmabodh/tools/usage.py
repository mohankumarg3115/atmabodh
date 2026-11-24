"""Phone usage tools (source: "usage").

On Android: UsageStatsManager polled from a foreground service.
We chose it over AccessibilityService on purpose: it only tells us WHICH
app is open and for how long, it cannot read what is on the screen.
"""
from atmabodh.data import store


def get_screen_history(days: int = 60) -> list[dict]:
    """Minutes of screen time after 11 PM, per night (model input only)."""
    n = store.read("nights").tail(days)
    return n[["night_of", "late_screen_min"]].to_dict("records")


def get_current_session() -> dict:
    """What is open right now. App name and category only, no content."""
    s = store.get_live_session()
    return {k: s[k] for k in ("now_h", "app", "category", "session_min",
                               "late_screen_min_tonight", "steps_today", "planned_wake_h") if k in s}
