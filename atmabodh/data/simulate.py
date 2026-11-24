"""Generate realistic, clearly SYNTHETIC data (8 weeks) for one student.

Why synthetic? For the prototype we need data we can demo anywhere,
offline. The Android app replaces this file with real readers
(Health Connect, UsageStatsManager, Calendar Provider).

The simulation encodes simple cause and effect, so the model has a
real pattern to learn:
    late screen time  -> later bedtime -> less sleep
    less sleep + debt -> next day: higher resting HR, lower HRV,
                         fewer steps, later first unlock
This simulated student is also personally sensitive to late screen
time (blue light, a racing mind), more than generic rules assume. That
is exactly what a personal model should discover and fixed rules miss.

The last 3 nights are forced to be late, and tomorrow has an exam:
that is the "12:05 AM Instagram" demo story.

Run:  python -m atmabodh.data.simulate
"""
import datetime as dt
import numpy as np

from atmabodh import config
from atmabodh.data import store

N_NIGHTS = 56          # 8 weeks


def generate(seed: int = 7, today: dt.date | None = None, path=None):
    rng = np.random.default_rng(seed)
    today = today or dt.date.today()
    first = today - dt.timedelta(days=N_NIGHTS)

    nights, days = [], []
    sleep_hist = []
    for i in range(N_NIGHTS):
        evening = first + dt.timedelta(days=i)
        forced_late = i >= N_NIGHTS - 3                      # last 3 nights
        late = forced_late or rng.random() < 0.3
        late_screen = rng.uniform(70, 120) if late else rng.uniform(5, 35)
        bedtime = 23.0 + 0.8 * late_screen / 60 + rng.normal(0, 0.25)
        if forced_late:
            bedtime = [25.0, 25.5, 26.0][i - (N_NIGHTS - 3)]
        wake = 7.4 + rng.normal(0, 0.25)
        sleep = round(max(3.5, 24 + wake - bedtime - 0.2), 2)
        sleep_hist.append(sleep)
        debt3 = sum(max(0.0, 7.5 - s) for s in sleep_hist[-3:])
        nights.append((evening.isoformat(), round(bedtime, 2), round(wake, 2), sleep, round(late_screen, 1)))

        # The NEXT day's body response to this night
        nxt = evening + dt.timedelta(days=1)
        short = 7.5 - sleep
        rhr = 62 + 1.6 * short + 0.5 * debt3 + 0.03 * late_screen + rng.normal(0, 1.0)
        hrv = 55 - 4.0 * short - 1.5 * debt3 - 0.08 * late_screen + rng.normal(0, 2.5)
        steps = 7800 + 700 * (sleep - 7.5) - 15 * late_screen + rng.normal(0, 700)
        unlock = wake + 0.35 * max(0.0, short) + rng.normal(0, 0.15)
        days.append((nxt.isoformat(), round(max(800, steps)), round(rhr, 1), round(hrv, 1), round(unlock, 2)))

    events = [
        ((today + dt.timedelta(days=1)).isoformat() + "T10:00", "Exam: Signals and Systems", 1),
        ((today + dt.timedelta(days=3)).isoformat() + "T14:00", "Lab record submission", 1),
        ((today + dt.timedelta(days=5)).isoformat() + "T18:00", "Cricket practice", 0),
    ]
    live = {  # what the phone sees right now: 12:05 AM tonight
        "now_h": 24.08,
        "app": "Instagram", "category": "social", "session_min": 40,
        "late_screen_min_tonight": 70,
        "steps_today": 3100,
        "planned_wake_h": 7.5,
    }

    with store.connect(path) as con:
        for t in ("nights", "days", "events"):
            con.execute(f"DELETE FROM {t}")
        con.executemany("INSERT INTO nights VALUES (?,?,?,?,?)", nights)
        con.executemany("INSERT INTO days VALUES (?,?,?,?,?)", days)
        con.executemany("INSERT INTO events VALUES (?,?,?)", events)
    store.set_live_session(live, path)
    return len(nights)


if __name__ == "__main__":
    n = generate()
    print(f"Wrote {n} nights of SYNTHETIC data to {config.DB_PATH}")
