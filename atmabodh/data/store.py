"""The on-device data store.

Two tables of *daily aggregates* (never raw sensor streams):

nights  - one row per evening: bedtime, wake time, sleep hours,
          screen minutes after 11 PM
days    - one row per day: steps, resting heart rate, HRV, first phone
          unlock time (these describe how the body responded to the
          previous night)

Plus calendar `events` and the `live_session` (which app is open right now).

On Android these come from Health Connect, UsageStatsManager and the
Calendar Provider, and are stored in Room + SQLCipher (encrypted).
"""
import json
import sqlite3
import pandas as pd

from atmabodh import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS nights (
    night_of TEXT PRIMARY KEY,   -- date of the evening (YYYY-MM-DD)
    bedtime_h REAL,              -- 25.5 = 1:30 AM
    wake_h REAL,                 -- 7.5  = 7:30 AM
    sleep_h REAL,
    late_screen_min REAL         -- screen time after 11 PM
);
CREATE TABLE IF NOT EXISTS days (
    date TEXT PRIMARY KEY,
    steps REAL,
    resting_hr REAL,             -- from the watch / band
    hrv_ms REAL,                 -- NULL if the wearable does not share it
    first_unlock_h REAL          -- first phone unlock that morning
);
CREATE TABLE IF NOT EXISTS events (
    start_iso TEXT,
    title TEXT,
    important INTEGER
);
CREATE TABLE IF NOT EXISTS live_session (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    json TEXT
);
"""


def connect(path=None):
    config.ensure_home()
    con = sqlite3.connect(path or config.DB_PATH)
    con.executescript(SCHEMA)
    return con


def read(table: str, path=None) -> pd.DataFrame:
    with connect(path) as con:
        return pd.read_sql_query(f"SELECT * FROM {table}", con)


def get_live_session(path=None) -> dict:
    with connect(path) as con:
        row = con.execute("SELECT json FROM live_session WHERE id = 1").fetchone()
    return json.loads(row[0]) if row else {}


def set_live_session(session: dict, path=None):
    with connect(path) as con:
        con.execute("INSERT OR REPLACE INTO live_session (id, json) VALUES (1, ?)", (json.dumps(session),))
