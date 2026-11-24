"""Calendar tools (source: "calendar").

On Android: the Calendar Provider, which reads calendars already synced
to the phone. No Google sign-in, nothing leaves the device.
"""
import datetime as dt

from atmabodh.data import store


def get_next_important_event(within_h: float = 14, now: dt.datetime | None = None,
                             now_h: float | None = None) -> dict | None:
    """The next important event within `within_h` hours, or None.

    `now_h` lets the demo pretend it is 12:05 AM (24.08) tonight.
    """
    if now is None:
        today = dt.datetime.combine(dt.date.today(), dt.time())
        now = today + dt.timedelta(hours=now_h) if now_h is not None else dt.datetime.now()
    ev = store.read("events")
    best = None
    for _, e in ev.iterrows():
        if not e["important"]:
            continue
        start = dt.datetime.fromisoformat(e["start_iso"])
        hours = (start - now).total_seconds() / 3600
        if 0 < hours <= within_h and (best is None or hours < best["starts_in_h"]):
            best = {"title": e["title"], "starts_in_h": round(hours, 1),
                    "starts_at": start.strftime("%I:%M %p").lstrip("0")}
    return best
