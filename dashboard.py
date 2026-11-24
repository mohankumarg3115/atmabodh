"""AtmaBodh dashboard (prototype of the app screens).

    streamlit run dashboard.py

Shows: consent switches per data source, the energy history the model
learned from, "Why was today bad?", the 12:05 AM real-time nudge, and
the access log. All local.
"""
import pandas as pd
import streamlit as st

from atmabodh import config
from atmabodh.data import simulate
from atmabodh.engine.insights import why_today
from atmabodh.engine.nudge import check_and_nudge, load_model
from atmabodh.engine.predictor import backtest
from atmabodh.gate import PrivacyGate

st.set_page_config(page_title="AtmaBodh", page_icon="🧭", layout="wide")
if not config.DB_PATH.exists():
    simulate.generate()
gate = PrivacyGate()

# ---- Sidebar: consent ---------------------------------------------------
st.sidebar.title("Your data, your rules")
st.sidebar.caption("Each source is a separate MCP server. Switch any off and the AI cannot read it.")
labels = {"body": "Body (sleep, heart rate, steps)", "usage": "Phone usage (which app is open)",
          "calendar": "Calendar (exams, events)"}
consent = gate.consent()
for src, lab in labels.items():
    new = st.sidebar.toggle(lab, value=consent[src], key=f"c_{src}")
    if new != consent[src]:
        gate.set_consent(src, new)
st.sidebar.divider()
use_llm = st.sidebar.toggle("Word nudges with local LLM (Ollama)", value=False)
if st.sidebar.button("Reset demo data"):
    simulate.generate()
    st.rerun()
st.sidebar.caption("Demo uses SYNTHETIC data. Nothing leaves this device.")

st.title("AtmaBodh")
st.caption("Private, on-device AI that predicts tomorrow's energy and nudges you in time")

model, train = load_model(gate, "dashboard refresh")
if model is None:
    st.warning("Body or usage data is switched off, so the personal model cannot run. Switch them on in the sidebar.")
else:
    c1, c2, c3 = st.columns(3)
    w = why_today(model, train)
    bt = backtest(train)
    c1.metric("Today's Energy Score", f"{w['energy_today']:.0f}/100")
    c2.metric("Personal model", f"{model.mode.title()}  ·  {model.n_days} days")
    c3.metric("Backtest error (last 7 days)", f"± {bt['mae_model']} pts")

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Energy Score history")
        chart = train.assign(date=pd.to_datetime(train["night_of"]) + pd.Timedelta(days=1)).set_index("date")
        chart["Predicted"] = [model.predict(r) for r in chart[["expected_sleep_h", "late_screen_min", "sleep_debt_3d", "steps_today"]].to_dict("records")]
        st.line_chart(chart.rename(columns={"energy_next": "Actual (from body signals)"})[["Actual (from body signals)", "Predicted"]])
    with right:
        st.subheader("Why was today bad?")
        for r in w["reasons"] or ["Nothing stands out: a normal day."]:
            st.write("• " + r)

st.divider()
st.subheader("Real-time check: 12:05 AM, Instagram open for 40 minutes")
if st.button("Run the Event Engine now", type="primary"):
    res = check_and_nudge(gate, use_llm=use_llm, ignore_cap=True)
    for s in res["steps"]:
        st.write("› " + s)
    if res["nudge"]:
        st.success(f"🔔 {res['text']}")
        st.caption(f"Text by: {res['text_source']}. Numbers by: personal model.")
    else:
        st.info(f"No nudge: {res['why']}")

st.divider()
st.subheader("Access log")
st.caption("Every read by the AI: what, when and why. The data itself is never logged.")
log = gate.read_log(last=15)
if log:
    st.dataframe(pd.DataFrame(log[::-1]), hide_index=True)
