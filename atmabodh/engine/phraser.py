"""Step 4: turn the decision into a friendly sentence.

Rule of the design: NUMBERS come from the model, WORDS come from the LLM.
The LLM never predicts anything, it only rewrites facts we give it, so
it cannot invent a wrong number.

The LLM runs locally (Ollama on a laptop; Gemma 4 E2B on LiteRT-LM on
the phone). If no local LLM is running, a template is used instead, so
the app always works, even offline with no model installed.
"""
import json
import urllib.request

from atmabodh import config


def template_nudge(f: dict) -> str:
    event = f" and {f['event_title']} at {f['event_time']}" if f.get("event_title") else ""
    return (f"{f['late_nights']} late nights in a row{event}. "
            f"Sleep now and tomorrow's energy is about {f['energy_if_sleep_now']:.0f}%. "
            f"One more hour on {f['app']} drops it to about {f['energy_if_one_more_hour']:.0f}%.")


def llm_nudge(facts: dict, timeout: float = 20) -> str | None:
    prompt = ("Write ONE short, kind phone notification (max 30 words) for a college student. "
              "Use only these facts and keep every number exactly as given:\n"
              + json.dumps(facts) + "\nNotification:")
    body = json.dumps({"model": config.LLM_MODEL, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0.3}}).encode()
    req = urllib.request.Request(config.LLM_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            text = json.loads(r.read())["response"].strip().strip('"')
        return text or None
    except Exception:
        return None


def phrase(facts: dict, use_llm: bool = True) -> tuple[str, str]:
    """Returns (text, source) where source is 'local-llm' or 'template'."""
    if use_llm:
        text = llm_nudge(facts)
        if text:
            return text, "local-llm"
    return template_nudge(facts), "template"
