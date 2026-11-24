"""Step 2: predict TOMORROW's Energy Score from TONIGHT's behaviour.

Inputs (tonight's behaviour)            Label (tomorrow's body response)
  expected_sleep_h                        Energy Score of the next day
  late_screen_min  (after 11 PM)          (calculated by energy.py)
  sleep_debt_3d    (last 3 nights)
  steps_today

Inputs and label come from DIFFERENT things (behaviour vs body
response), so the model learns something real instead of re-learning
the formula.

Cold start: until we have COLD_START_DAYS labelled days, we use fixed
rules. After that, a personal Ridge regression takes over. Ridge is
linear regression with a penalty on large weights, which keeps it
stable when we only have a few weeks of data.

Both modes can EXPLAIN a prediction: each input's contribution in
points, relative to the user's usual value. That powers
"Why was today bad?".
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from atmabodh import config
from atmabodh.engine.energy import energy_scores

FEATURES = ["expected_sleep_h", "late_screen_min", "sleep_debt_3d", "steps_today"]


class RidgeRegression:
    """Ridge regression written from scratch with numpy (no scikit-learn).

    1. Standardise each input: z = (x - mean) / std, so hours, minutes
       and steps are on the same scale and the weights are comparable.
    2. Solve for the weights w in closed form:
           w = (Zᵀ Z + alpha · I)⁻¹ Zᵀ (y - mean_y)
       Plain linear regression is the same formula with alpha = 0.
       The "+ alpha · I" is the safety brake: it pulls weights towards 0,
       so a few weeks of noisy data cannot produce wild predictions.
    3. Predict: y = mean_y + z · w
    """

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha

    def fit(self, X: np.ndarray, y: np.ndarray):
        X, y = np.asarray(X, float), np.asarray(y, float)
        self.mean_ = X.mean(axis=0)
        self.scale_ = X.std(axis=0)
        self.scale_[self.scale_ == 0] = 1.0
        Z = (X - self.mean_) / self.scale_
        self.intercept_ = y.mean()
        A = Z.T @ Z + self.alpha * np.eye(Z.shape[1])
        self.coef_ = np.linalg.solve(A, Z.T @ (y - self.intercept_))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        Z = (np.asarray(X, float) - self.mean_) / self.scale_
        return self.intercept_ + Z @ self.coef_

# Cold-start rules: points per unit, relative to a reference value
RULES = {  # feature: (reference, points per unit)
    "expected_sleep_h": (7.5, +7.0),
    "late_screen_min": (30.0, -0.08),
    "sleep_debt_3d": (0.0, -3.0),
    "steps_today": (7000.0, +0.0008),
}
RULE_BASE = 60.0


def build_training_frame(body_history: dict, screen_history: list[dict]) -> pd.DataFrame:
    """One row per night: tonight's inputs + tomorrow's energy (label)."""
    nights = pd.DataFrame(body_history["nights"])
    days = energy_scores(pd.DataFrame(body_history["days"]))
    screen = pd.DataFrame(screen_history)
    df = nights.merge(screen, on="night_of", how="left").sort_values("night_of").reset_index(drop=True)

    usual = df["sleep_h"].expanding().median().shift(1).fillna(config.USUAL_SLEEP_H)
    short = (usual - df["sleep_h"]).clip(lower=0)
    df["sleep_debt_3d"] = short.shift(1).rolling(3, min_periods=1).sum().fillna(0)
    df["expected_sleep_h"] = df["sleep_h"]

    by_date = days.set_index("date")
    next_day = (pd.to_datetime(df["night_of"]) + pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
    df["steps_today"] = df["night_of"].map(by_date["steps"])
    df["energy_next"] = next_day.map(by_date["energy"])
    df["steps_today"] = df["steps_today"].fillna(df["steps_today"].median())
    return df.dropna(subset=["energy_next"]).reset_index(drop=True)


@dataclass
class PersonalModel:
    mode: str = "rules"
    ridge: object = None
    means: dict = field(default_factory=dict)
    n_days: int = 0

    def fit(self, train: pd.DataFrame):
        self.n_days = len(train)
        self.means = train[FEATURES].mean().to_dict() if len(train) else {}
        if len(train) < config.COLD_START_DAYS:
            self.mode = "rules"
            return self
        self.mode = "ridge"
        self.ridge = RidgeRegression(alpha=config.RIDGE_ALPHA).fit(train[FEATURES].values, train["energy_next"].values)
        return self

    def predict(self, x: dict) -> float:
        if self.mode == "rules":
            score = RULE_BASE + sum(w * (x[f] - ref) for f, (ref, w) in RULES.items())
        else:
            score = float(self.ridge.predict(np.array([[x[f] for f in FEATURES]]))[0])
        return float(np.clip(score, 0, 100))

    def contributions(self, x: dict) -> dict:
        """Points each input adds (+) or removes (-) vs the user's usual."""
        if self.mode == "rules":
            ref = {f: self.means.get(f, r) for f, (r, _) in RULES.items()}
            return {f: w * (x[f] - ref[f]) for f, (_, w) in RULES.items()}
        r = self.ridge
        return {f: float(r.coef_[i] * (x[f] - r.mean_[i]) / r.scale_[i])
                for i, f in enumerate(FEATURES)}

    def explain(self, x: dict, top: int = 3) -> list[str]:
        """Plain-language reasons, worst first (only the negative ones)."""
        c = self.contributions(x)
        usual = self.means
        text = {
            "expected_sleep_h": lambda v: f"Only {v:.1f} h of sleep (your usual is {usual.get('expected_sleep_h', 7.5):.1f} h)",
            "late_screen_min": lambda v: f"{v:.0f} min of screen time after 11 PM (usual {usual.get('late_screen_min', 30):.0f} min)",
            "sleep_debt_3d": lambda v: f"{v:.1f} h of sleep debt from the last 3 nights",
            "steps_today": lambda v: f"Only {v:,.0f} steps (usual {usual.get('steps_today', 7000):,.0f})",
        }
        bad = sorted((p, f) for f, p in c.items() if p < -0.5)
        return [f"{text[f](x[f])}  ({p:+.0f} pts)" for p, f in bad[:top]]


def backtest(train: pd.DataFrame, holdout: int = 7) -> dict:
    """How well does the personal model predict the last `holdout` days,
    compared with the fixed rules? (mean absolute error, in points)"""
    fit_part, test = train.iloc[:-holdout], train.iloc[-holdout:]
    model = PersonalModel().fit(fit_part)
    rules = PersonalModel()
    rules.means = fit_part[FEATURES].mean().to_dict()
    err = lambda m: float(np.mean([abs(m.predict(r) - r["energy_next"]) for r in test[FEATURES + ["energy_next"]].to_dict("records")]))
    return {"model": model.mode, "mae_model": round(err(model), 1), "mae_rules": round(err(rules), 1), "days_tested": holdout}
