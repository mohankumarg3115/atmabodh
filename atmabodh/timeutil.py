"""Time helpers.

Night-time hours are stored as a float that keeps counting past midnight,
so 23.5 = 11:30 PM, 24.0 = 12:00 AM, 25.5 = 1:30 AM. This makes
"sleep hours = (24 + wake) - bedtime" simple maths.
"""


def fmt_hour(h: float) -> str:
    """25.5 -> '1:30 AM'"""
    h = h % 24
    hour, minute = int(h), int(round((h - int(h)) * 60))
    if minute == 60:
        hour, minute = (hour + 1) % 24, 0
    suffix = "AM" if hour < 12 else "PM"
    hour12 = hour % 12 or 12
    return f"{hour12}:{minute:02d} {suffix}"
