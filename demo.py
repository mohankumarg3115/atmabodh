"""AtmaBodh terminal demo: the 12:05 AM Instagram story, end to end.

    python demo.py                 # full demo (uses a local LLM if Ollama is running)
    python demo.py --no-llm        # template text only
    python demo.py --calendar-off  # show the privacy gate refusing calendar access

Everything runs locally. Turn off Wi-Fi before running: it still works.
"""
import argparse

from atmabodh import config
from atmabodh.data import simulate
from atmabodh.engine.insights import why_today
from atmabodh.engine.nudge import check_and_nudge, load_model
from atmabodh.engine.predictor import backtest
from atmabodh.gate import PrivacyGate


def line(title=""):
    print("\n" + "-" * 70 + (f"\n{title}" if title else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--calendar-off", action="store_true")
    args = ap.parse_args()

    if not config.DB_PATH.exists():
        simulate.generate()
        print("Created 8 weeks of SYNTHETIC student data (no real data is used).")

    gate = PrivacyGate()
    gate.set_consent("calendar", not args.calendar_off)
    print(f"Consent: {gate.consent()}")

    line("1) PERSONAL MODEL")
    model, train = load_model(gate)
    print(f"Mode: {model.mode} (trained on {model.n_days} days of this user's data)")
    bt = backtest(train)
    print(f"Backtest: trained without the last {bt['days_tested']} days, then predicted them. Mean error: {bt['mae_model']} pts")

    line("2) MORNING INSIGHT: why was today bad?")
    w = why_today(model, train)
    print(f"Today's Energy Score: {w['energy_today']:.0f}/100")
    for r in w["reasons"]:
        print("  -", r)

    line("3) REAL-TIME CHECK (Event Engine woke up: an app came to the foreground)")
    result = check_and_nudge(gate, use_llm=not args.no_llm, ignore_cap=True)
    for s in result["steps"]:
        print("  >", s)
    if result["nudge"]:
        print(f"\n  NOTIFICATION ({result['text_source']}):\n  \"{result['text']}\"")
    else:
        print(f"\n  No nudge: {result['why']}")

    line("4) ACCESS LOG (what was read, when and why; never the data itself)")
    for e in gate.read_log(last=8):
        mark = "allowed" if e["allowed"] else "BLOCKED"
        print(f"  {e['time']}  {e['source']:<9} {e['tool']:<26} {mark:<8} {e['reason']}")
    line()


if __name__ == "__main__":
    main()
