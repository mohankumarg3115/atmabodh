"""Run:  python -m pytest -q"""
import os
import tempfile

os.environ["ATMABODH_HOME"] = tempfile.mkdtemp()

from atmabodh.data import simulate  # noqa: E402
from atmabodh.engine.nudge import check_and_nudge, load_model  # noqa: E402
from atmabodh.engine.predictor import PersonalModel  # noqa: E402
from atmabodh.gate import PrivacyGate  # noqa: E402

simulate.generate(seed=1)


def test_model_learns_that_less_sleep_means_less_energy():
    model, _ = load_model(PrivacyGate())
    base = {"expected_sleep_h": 7.5, "late_screen_min": 20, "sleep_debt_3d": 0, "steps_today": 7500}
    tired = dict(base, expected_sleep_h=5.0, sleep_debt_3d=5)
    assert model.mode == "ridge"
    assert model.predict(tired) < model.predict(base)


def test_cold_start_uses_rules():
    _, train = load_model(PrivacyGate())
    assert PersonalModel().fit(train.head(5)).mode == "rules"


def test_nudge_fires_in_the_12am_story():
    res = check_and_nudge(PrivacyGate(), use_llm=False, ignore_cap=True)
    assert res["nudge"]
    assert res["facts"]["energy_if_sleep_now"] > res["facts"]["energy_if_one_more_hour"]


def test_gate_blocks_and_logs_when_consent_is_off():
    gate = PrivacyGate()
    gate.set_consent("body", False)
    res = check_and_nudge(gate, use_llm=False, ignore_cap=True)
    assert not res["nudge"]
    assert any(e["source"] == "body" and not e["allowed"] for e in gate.read_log())
    gate.set_consent("body", True)
