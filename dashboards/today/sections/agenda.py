"""Agenda section: calendar events and to-do tasks for the next few days.

Two styles:
    rows     (default) one band per day, sized to its events (at most
             max_events lines), then today's to-dos in whatever space is left.
             On a busy day the to-dos are left out.
    columns  days side by side, events on top and that day's to-dos at the
             bottom of each column.

Config (dashboards.today.agenda in config.yaml):
    style            rows or columns (default rows)
    days             number of days, today first (default 2 for rows, 3 for columns)
    max_events       rows: event lines per day, the last one becomes
                     "+N more" when there are too many (default 5)
    calendars        list of private iCal (.ics) addresses. These are secrets:
                     anyone with the address can read the calendar. Keep them
                     only in config.yaml.
    todoist_token    Todoist API token (secret; config.yaml only). Blank -> no tasks.
    todoist_filter   Todoist filter for which tasks to show
                     (default "overdue | next 7 days"); only tasks due inside
                     the shown days are drawn, overdue ones go to today.
    max_tasks        columns: tasks shown per day before "…" (default 2)
    simulate         true -> made up SAMPLE events and tasks, no network

Events that have already ended disappear from today. All day events show
"All day". Each run fetches fresh data, so a broken address makes the whole
dashboard show its "stale since" note instead of silently dropping events.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from dashlib.timeutil import to_datetime

TIMEOUT_SECONDS = 20
TODOIST_URL = "https://api.todoist.com/api/v1/tasks/filter"
TODOIST_DEFAULT_FILTER = "overdue | next 7 days"
TODOIST_MAX_PAGES = 5
USER_AGENT = "dashboard/0.1"


# ----- fetch ---------------------------------------------------------------
def _style(config) -> str:
    style = str(config.get("style") or "rows")
    if style not in ("rows", "columns"):
        raise ValueError("agenda.style must be rows or columns")
    return style


def _days(config) -> int:
    try:
        n = int(config.get("days") or (2 if _style(config) == "rows" else 3))
    except (TypeError, ValueError):
        raise ValueError("agenda.days must be a whole number") from None
    if not 1 <= n <= 7:
        raise ValueError("agenda.days must be from 1 to 7")
    return n


def _get(url: str, headers: dict | None = None) -> bytes:
    if not url.startswith("https://"):
        raise ValueError("agenda: only https addresses are allowed")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        return resp.read()


def _calendar_events(ics: bytes, start: datetime, end: datetime, tz) -> list[dict]:
    import icalendar
    import recurring_ical_events

    cal = icalendar.Calendar.from_ical(ics)
    out = []
    for ev in recurring_ical_events.of(cal).between(start, end):
        if str(ev.get("STATUS", "")).upper() == "CANCELLED":
            continue
        s, e = ev.get("DTSTART"), ev.get("DTEND")
        s = s.dt if s else None
        e = e.dt if e else None
        title = str(ev.get("SUMMARY") or "(no title)").strip()
        if isinstance(s, datetime):
            s = s if s.tzinfo else s.replace(tzinfo=tz)
            e = e if isinstance(e, datetime) else s
            e = e if e.tzinfo else e.replace(tzinfo=tz)
            out.append({"title": title, "start": s.isoformat(), "end": e.isoformat(), "all_day": False})
        elif isinstance(s, date):
            e = e if isinstance(e, date) and not isinstance(e, datetime) else s + timedelta(days=1)
            out.append({"title": title, "start": s.isoformat(), "end": e.isoformat(), "all_day": True})
    return out


_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def _plain(text: str) -> str:
    """Todoist content is Markdown; keep the words only."""
    text = _MD_LINK.sub(r"\1", str(text or ""))
    return re.sub(r"[*_`]+", "", text).strip()


def _todoist_tasks(token: str, query: str) -> list[dict]:
    out, cursor = [], None
    for _ in range(TODOIST_MAX_PAGES):
        params = {"query": query, "limit": 200}
        if cursor:
            params["cursor"] = cursor
        raw = json.loads(_get(f"{TODOIST_URL}?{urllib.parse.urlencode(params)}",
                              {"Authorization": f"Bearer {token}"}).decode("utf-8"))
        items = raw.get("results", []) if isinstance(raw, dict) else raw
        for t in items or []:
            due = (t.get("due") or {}).get("date") if isinstance(t, dict) else None
            if not due or t.get("checked") or t.get("is_deleted"):
                continue
            out.append({"text": _plain(t.get("content")), "due": str(due)[:10],
                        "priority": int(t.get("priority") or 1), "order": t.get("child_order") or 0})
        cursor = raw.get("next_cursor") if isinstance(raw, dict) else None
        if not cursor:
            break
    return out


def _simulated(today: date, tz) -> dict:
    def at(d, h, m=0):
        return datetime.combine(today + timedelta(days=d), time(h, m), tz).isoformat()
    ev = [("Coco piano lesson", 0, 17, 30), ("Call parents", 0, 20, 0),
          ("Dentist", 1, 9, 0), ("Workout", 1, 13, 0), ("Dinner with friends at the harbour", 1, 18, 0),
          ("School meeting", 2, 15, 0)]
    events = [{"title": t, "start": at(d, h, m), "end": at(d, h + 1, m), "all_day": False} for t, d, h, m in ev]
    events.append({"title": "Recycling pickup", "start": (today + timedelta(days=2)).isoformat(),
                   "end": (today + timedelta(days=3)).isoformat(), "all_day": True})
    tk = [("Renew library books", -2), ("Reply to the school email", 0), ("Buy birthday card", 0),
          ("Book car service", 1), ("Water the plants", 2)]
    tasks = [{"text": t, "due": (today + timedelta(days=d)).isoformat(), "priority": 1, "order": i}
             for i, (t, d) in enumerate(tk)]
    return {"events": events, "tasks": tasks}


def fetch(config: dict) -> dict:
    tz = ZoneInfo(config.get("timezone") or "UTC")
    n = _days(config)
    today = datetime.now(tz).date()
    data = {"status": "ok", "sample": bool(config.get("simulate")), "days": n,
            "style": _style(config), "max_tasks": config.get("max_tasks") or 2,
            "max_events": config.get("max_events") or 5}
    if config.get("simulate"):
        return {**data, **_simulated(today, tz)}

    start = datetime.combine(today, time(0), tz)
    end = start + timedelta(days=n)
    calendars = config.get("calendars") or []
    if isinstance(calendars, str):
        calendars = [calendars]
    events = []
    for url in calendars:
        if url:
            events += _calendar_events(_get(str(url).strip()), start, end, tz)

    tasks = []
    token = str(config.get("todoist_token") or "").strip()
    if token:
        query = str(config.get("todoist_filter") or TODOIST_DEFAULT_FILTER)
        tasks = _todoist_tasks(token, query)
    if not calendars and not token:
        data["status"] = "not_configured"
    return {**data, "events": events, "tasks": tasks}


# ----- layout --------------------------------------------------------------
def _event_days(ev: dict, tz) -> tuple[date, date]:
    """First and last local day an event covers."""
    if ev.get("all_day"):
        s = date.fromisoformat(ev["start"][:10])
        e = date.fromisoformat(ev["end"][:10]) - timedelta(days=1)
        return s, max(s, e)
    s = to_datetime(ev["start"]).astimezone(tz)
    e = to_datetime(ev["end"]).astimezone(tz)
    last = (e - timedelta(microseconds=1)).date() if e > s else s.date()
    return s.date(), last


def layout(data: dict, ctx) -> list[dict]:
    if data.get("status") == "not_configured":
        return [{"type": "text", "text": "Agenda: add calendars or todoist_token in config.yaml",
                 "size": "small"}]
    tz, now = ctx.tz, ctx.now
    today = now.astimezone(tz).date()
    n = int(data.get("days") or 3)
    days = [today + timedelta(days=i) for i in range(n)]

    columns = []
    for i, day in enumerate(days):
        timed, all_day = [], []
        for ev in data.get("events") or []:
            try:
                first, last = _event_days(ev, tz)
            except (KeyError, TypeError, ValueError):
                continue
            if not first <= day <= last:
                continue
            if ev.get("all_day") or first < day:
                all_day.append({"time": "All day", "text": ev.get("title", ""), "_k": ""})
                continue
            if i == 0 and to_datetime(ev["end"]) <= now:
                continue  # already over
            start = to_datetime(ev["start"])
            timed.append({"time": ctx.format_time(start, "clock"), "text": ev.get("title", ""),
                          "_k": start.isoformat()})
        events = all_day + sorted(timed, key=lambda e: e["_k"])
        for e in events:
            e.pop("_k", None)

        tasks = []
        for t in data.get("tasks") or []:
            try:
                due = date.fromisoformat(str(t.get("due"))[:10])
            except ValueError:
                continue
            if due == day or (i == 0 and due < day):
                tasks.append(t)
        tasks.sort(key=lambda t: (t.get("due", ""), -int(t.get("priority") or 1), t.get("order") or 0))

        title = "Today" if i == 0 else f"{day:%a} {day.day}"
        columns.append({"title": title, "label": "Today" if i == 0 else f"{day:%a}", "sub": str(day.day),
                        "events": events, "tasks": [t["text"] for t in tasks]})

    out = []
    if data.get("sample"):
        out.append({"type": "text", "text": "SAMPLE agenda (simulate: true), not real", "size": 20,
                    "bold": True})
    if data.get("style") == "columns":
        out.append({"type": "divider"})
        out.append({"type": "days", "columns": columns, "max_tasks": data.get("max_tasks") or 2})
        return out
    rows = [{"label": col["label"], "sub": col["sub"], "short": col["title"], "events": col["events"]}
            for col in columns]
    out.append({"type": "dayrows", "rows": rows, "max_lines": data.get("max_events") or 5,
                "list": columns[0]["tasks"] if columns else [], "list_title": "To do today"})
    return out
