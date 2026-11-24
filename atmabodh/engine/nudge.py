"""Step 3: the real-time decision. Should we nudge RIGHT NOW?

Called by the Event Engine whenever an app comes to the foreground
(on Android: a foreground service polling UsageStatsManager).

We nudge only when three things line up, so the user is not spammed:
  1. LATE + DISTRACTING: after 11:30 PM, on a social/video/game app
     for 20+ minutes
  2. TIRED BODY: 2+ late nights in the last 3, or 2+ hours sleep debt
  3. BIG EVENT: an important calendar event in the next 14 hours
     (if the user turned the calendar off, we skip this check)
Plus a daily cap of MAX_NUDGES_PER_DAY.

Then we ask the personal model two "what if" questions:
  - what if you sleep now?
  - what if you stay on this app for one more hour?
and show the difference. Every data read goes through the Privacy Gate.
"""
import datetime as dt
import json

from atmabodh import config
from atmabodh.engine.phraser import phrase
from atmabodh.engine.predictor import PersonalModel, build_training_frame
from atmabodh.gate import PrivacyGate
from atmabodh.timeutil import fmt_hour
from atmabodh.tools import body, calendar, usage

WIND_DOWN_H = 0.25   # assume 15 min to fall asleep after closing the app


def load_model(gate: PrivacyGate, reason: str = "update personal model"):
    bh = gate.call("body", body.get_body_history, reason, days=60)
    sh = gate.call("usage", usage.get_screen_history, reason, days=60)
    if bh is None or sh is None:
        return None, None
    train = build_training_frame(bh, sh)
    return PersonalModel().fit(train), train


def _nudges_today() -> int:
    today = dt.date.today().isoformat()
    try:
        lines = config.NUDGE_LOG_PATH.read_text().splitlines()
    except FileNotFoundError:
        return 0
    return sum(1 for l in lines if json.loads(l)["time"].startswith(today))


def check_and_nudge(gate: PrivacyGate | None = None, use_llm: bool = True, ignore_cap: bool = False) -> dict:
    gate = gate or PrivacyGate()
    steps = []   # a readable trace, shown in the demo and dashboard

    session = gate.call("usage", usage.get_current_session, "real-time app check")
    if session is None:
        return {"nudge": False, "why": "Usage access is switched off", "steps": steps}
    steps.append(f"{fmt_hour(session['now_h'])}: {session['app']} open for {session['session_min']} min")

    late = (session["now_h"] >= config.LATE_NIGHT_FROM_H and session["category"] in config.DISTRACTING
            and session["session_min"] >= config.MIN_SESSION_MIN)
    if not late:
        return {"nudge": False, "why": "Not a late-night distracting session", "steps": steps}

    sleep = gate.call("body", body.get_sleep_summary, "bedtime check")
    if sleep is None:
        return {"nudge": False, "why": "Body data is switched off", "steps": steps}
    steps.append(f"Last {sleep['nights']} nights: {sleep['late_nights']} late, avg {sleep['avg_sleep_h']} h sleep, "
                 f"{sleep['sleep_debt_h']} h debt")
    tired = sleep["late_nights"] >= 2 or sleep["sleep_debt_h"] >= 2
    if not tired:
        return {"nudge": False, "why": "Body is rested enough", "steps": steps}

    event = gate.call("calendar", calendar.get_next_important_event, "is there a big day tomorrow?",
                      within_h=config.EVENT_WINDOW_H, now_h=session["now_h"])
    if not gate.consent()["calendar"]:
        steps.append("Calendar is switched off: the gate blocked it, deciding without it")
    elif event is None:
        return {"nudge": False, "why": "No important event soon", "steps": steps}
    else:
        steps.append(f"Calendar: {event['title']} in {event['starts_in_h']} h")

    if not ignore_cap and _nudges_today() >= config.MAX_NUDGES_PER_DAY:
        return {"nudge": False, "why": "Daily nudge limit reached", "steps": steps}

    model, _ = load_model(gate, "what-if prediction")
    wake = session["planned_wake_h"] + 24
    def scenario(bedtime_h, extra_screen):
        return {"expected_sleep_h": max(0.0, wake - bedtime_h),
                "late_screen_min": session["late_screen_min_tonight"] + extra_screen,
                "sleep_debt_3d": sleep["sleep_debt_h"],
                "steps_today": session["steps_today"]}
    now_x = scenario(session["now_h"] + WIND_DOWN_H, 0)
    later_x = scenario(session["now_h"] + 1 + WIND_DOWN_H, 60)
    e_now, e_later = model.predict(now_x), model.predict(later_x)
    steps.append(f"Model ({model.mode}, {model.n_days} days): sleep now -> {e_now:.0f}%, one more hour -> {e_later:.0f}%")

    facts = {"app": session["app"], "late_nights": sleep["late_nights"],
             "energy_if_sleep_now": round(e_now), "energy_if_one_more_hour": round(e_later)}
    if event:
        facts.update(event_title=event["title"], event_time=event["starts_at"])
    text, source = phrase(facts, use_llm=use_llm)

    config.ensure_home()
    with open(config.NUDGE_LOG_PATH, "a") as f:
        f.write(json.dumps({"time": dt.datetime.now().isoformat(timespec="seconds"), "text": text}) + "\n")
    return {"nudge": True, "text": text, "text_source": source, "facts": facts,
            "reasons": model.explain(later_x), "steps": steps}
