"""Step 1: calculate an Energy Score (0-100) for each day, automatically.

No question to the user. We look at how the body behaved that day,
compared with THIS person's normal (their personal baseline):

    resting heart rate  higher than usual  -> tired
    HRV                 lower than usual   -> tired
    steps               lower than usual   -> tired
    first phone unlock  later than usual   -> tired

Each signal becomes a z-score: (value - usual) / usual spread.
We flip the signs so that "+" always means "more energy", average them,
and map to 0-100 around 60 (an ordinary day), 12 points per z.

If a signal is missing (e.g. no HRV from this wearable) it is simply
skipped, so phone-only users still get a score.
"""
import numpy as np
import pandas as pd

BASELINE_WINDOW = 28          # personal baseline = the previous 28 days
MIN_BASELINE = 7

# signal -> direction (+1: higher is better, -1: higher is worse)
SIGNALS = {"resting_hr": -1, "hrv_ms": +1, "steps": +1, "first_unlock_h": -1}


def energy_scores(days: pd.DataFrame) -> pd.DataFrame:
    """Add `energy` (0-100) to a frame of daily body data."""
    d = days.sort_values("date").reset_index(drop=True).copy()
    zs = []
    for col, sign in SIGNALS.items():
        if col not in d or d[col].isna().all():
            continue
        past = d[col].shift(1).rolling(BASELINE_WINDOW, min_periods=MIN_BASELINE)
        mean, std = past.mean(), past.std().replace(0, np.nan)
        # first week: compare against the first week itself
        mean = mean.fillna(d[col].iloc[:MIN_BASELINE].mean())
        std = std.fillna(d[col].iloc[:MIN_BASELINE].std() or 1.0)
        zs.append(sign * (d[col] - mean) / std)
    z = pd.concat(zs, axis=1).mean(axis=1, skipna=True)
    d["energy"] = (60 + 12 * z).clip(0, 100).round(0)
    return d
