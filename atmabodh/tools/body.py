"""Body data tools (source: "body").

On Android: Health Connect (sleep sessions, steps, resting heart rate,
HRV), which already merges data from WHOOP, Oura, Samsung, Noise, or
the phone itself.

Tools return daily aggregates or short summaries, never raw samples.
"""
from atmabodh import config
from atmabodh.data import store


def get_body_history(days: int = 60) -> dict:
    """Daily sleep and body aggregates for the last `days` days.

    Used by the on-device model only; never sent to the LLM.
    """
    nights = store.read("nights").tail(days)
    body = store.read("days").tail(days)
    return {"nights": nights[["night_of", "bedtime_h", "wake_h", "sleep_h"]].to_dict("records"),
            "days": body.to_dict("records")}


def get_sleep_summary(nights: int = 3) -> dict:
    """Short summary of the last few nights. Safe to give to the LLM."""
    n = store.read("nights")
    recent = n.tail(nights)
    usual = float(n["sleep_h"].iloc[:-nights].median()) if len(n) > nights + 6 else config.USUAL_SLEEP_H
    return {
        "nights": int(len(recent)),
        "avg_sleep_h": round(float(recent["sleep_h"].mean()), 1),
        "usual_sleep_h": round(usual, 1),
        "late_nights": int((recent["bedtime_h"] >= config.LATE_BEDTIME_H).sum()),
        "sleep_debt_h": round(float((usual - recent["sleep_h"]).clip(lower=0).sum()), 1),
    }
