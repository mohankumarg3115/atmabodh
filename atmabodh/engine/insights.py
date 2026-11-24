"""Morning insight: "Why was today bad?"

Takes last night's inputs, asks the personal model which ones pulled
today's energy down the most, and returns plain-language reasons.
"""
from atmabodh.engine.predictor import FEATURES, PersonalModel


def why_today(model: PersonalModel, train) -> dict:
    last = train.iloc[-1]
    x = {f: float(last[f]) for f in FEATURES}
    return {"date": last["night_of"], "energy_today": float(last["energy_next"]),
            "predicted": round(model.predict(x)), "reasons": model.explain(x)}
