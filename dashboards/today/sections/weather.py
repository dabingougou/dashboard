"""Weather section: current conditions, an hourly strip for the next 12 hours,
"feels like" and the next sunrise or sunset, from Open-Meteo.

Config (dashboards.today.weather in config.yaml):
    latitude, longitude      blank -> a "Set location in config.yaml" note
    temperature_unit         celsius | fahrenheit   (default celsius)
    wind_unit                kmh | ms | mph | kn    (default kmh)
    rain_threshold_percent   show the rain block at or above this (default 20)
    simulate                 true -> fake SAMPLE values, no network
    simulate_rain_percent    with simulate: peak rain chance to fake (default 40),
                             so both the rain shown and the dry look can be previewed
    tomorrow_tags            true -> short tags beside the date for what changes
                             tomorrow: warmer/cooler, windier/calmer, rainier/drier;
                             nothing shown when nothing changes (default false)
    simulate_tomorrow        with simulate: {temp: +/-deg, wind: +/-speed, rain: +/-points},
                             tomorrow's change versus today (default all 0)

Data source: https://open-meteo.com/ (free, no key; attribution required).
"""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from dashlib.timeutil import to_datetime

FOOTER_NOTE = "Weather: Open-Meteo.com"

API_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 15
HOURS_AHEAD = 3          # rain window: the current hour and the next 3
WIND_LATER_HOURS = 3     # forecast wind shown in parentheses
STRIP_HOURS = 12         # hourly strip: the current hour .. +12h
STRIP_MARK_EVERY = 4     # write the temperature at every 4th hour
FETCH_HOURS = STRIP_HOURS + 1

# Tomorrow versus today, compared on daily values (high temperature, strongest
# wind, highest rain chance). A tag shows only when the change reaches these.
TOMORROW_TEMP_DELTA = 3                                       # degrees
TOMORROW_WIND_DELTA = {"kmh": 10, "ms": 3, "mph": 6, "kn": 5}  # per wind unit
TOMORROW_RAIN_DELTA = 30                                      # percentage points

TEMP_UNITS = ("celsius", "fahrenheit")
WIND_UNITS = {"kmh": "km/h", "ms": "m/s", "mph": "mph", "kn": "kn"}

# WMO weather interpretation codes -> short condition word.
_WMO = {
    0: "Clear", 1: "Clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Fog",
    51: "Drizzle", 53: "Drizzle", 55: "Drizzle", 56: "Drizzle", 57: "Drizzle",
    61: "Rain", 63: "Rain", 65: "Rain", 66: "Rain", 67: "Rain",
    71: "Snow", 73: "Snow", 75: "Snow", 77: "Snow", 85: "Snow", 86: "Snow",
    80: "Showers", 81: "Showers", 82: "Showers",
    95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm",
}


# Condition word -> icon name (see dashlib.icons).
_ICON = {
    "Clear": "sun", "Partly cloudy": "partly_cloudy", "Overcast": "cloud",
    "Fog": "fog", "Drizzle": "drizzle", "Rain": "rain", "Showers": "rain",
    "Snow": "snow", "Thunderstorm": "thunder",
}


def condition(code) -> str:
    try:
        return _WMO.get(int(code), "")
    except (TypeError, ValueError):
        return ""


def condition_icon(code) -> str | None:
    return _ICON.get(condition(code))


# ----- fetch ---------------------------------------------------------------
def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def _num(v):
    """Float or None for missing/null/non numeric values."""
    if isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _at(seq, i):
    return seq[i] if isinstance(seq, list) and 0 <= i < len(seq) else None


def _settings(config: dict) -> dict:
    temp_unit = config.get("temperature_unit") or "celsius"
    wind_unit = config.get("wind_unit") or "kmh"
    if temp_unit not in TEMP_UNITS:
        raise ValueError(f"weather.temperature_unit must be one of {TEMP_UNITS}")
    if wind_unit not in WIND_UNITS:
        raise ValueError(f"weather.wind_unit must be one of {tuple(WIND_UNITS)}")
    threshold = config.get("rain_threshold_percent")
    threshold = 20 if _blank(threshold) else _num(threshold)
    if threshold is None:
        raise ValueError("weather.rain_threshold_percent must be a number")
    sim_rain = config.get("simulate_rain_percent")
    sim_rain = 40 if _blank(sim_rain) else _num(sim_rain)
    if sim_rain is None or not 0 <= sim_rain <= 100:
        raise ValueError("weather.simulate_rain_percent must be a number from 0 to 100")
    sim_t = config.get("simulate_tomorrow") or {}
    if not isinstance(sim_t, dict):
        raise ValueError("weather.simulate_tomorrow must be a mapping like {temp: -4, wind: 12, rain: 40}")
    sim_tomorrow = {}
    for k in ("temp", "wind", "rain"):
        v = 0 if _blank(sim_t.get(k)) else _num(sim_t.get(k))
        if v is None:
            raise ValueError(f"weather.simulate_tomorrow.{k} must be a number")
        sim_tomorrow[k] = v
    return {"temp_unit": temp_unit, "wind_unit": wind_unit, "threshold": threshold,
            "sim_rain": sim_rain, "sim_tomorrow": sim_tomorrow,
            "tomorrow_tags": config.get("tomorrow_tags") is True}


def _simulated(config: dict, s: dict) -> dict:
    tz = ZoneInfo(config.get("timezone") or "UTC")
    hour = datetime.now(tz).replace(minute=0, second=0, microsecond=0)
    # Peak at +2h; the other hours are lower, so the peak hour is unambiguous.
    peak = s["sim_rain"]
    shape = (0.25, 0.6, 1.0, 0.75, 0.5, 0.3, 0.2, 0.15, 0.1, 0.1, 0.05, 0.05, 0.05)
    probs = [round(peak * k) for k in shape[:FETCH_HOURS]]
    temps = [round(7.0 - 0.6 * i + (0.08 * i * i if i > 6 else 0), 1) for i in range(FETCH_HOURS)]
    day = hour.replace(hour=0)
    daily = _simulated_daily(peak, s["sim_tomorrow"])
    daily["sunrise"] = [(day + timedelta(days=d, hours=7, minutes=31)).isoformat() for d in (0, 1)]
    daily["sunset"] = [(day + timedelta(days=d, hours=16, minutes=27)).isoformat() for d in (0, 1)]
    return {
        "time": [(hour + timedelta(hours=i)).isoformat() for i in range(FETCH_HOURS)],
        "current": {"temperature_2m": 7.2, "apparent_temperature": 4.1, "wind_speed_10m": 18.4,
                    "weather_code": 2},
        "hourly": {"temperature_2m": temps,
                   "wind_speed_10m": [18, 19, 21, 24, 22, 20, 17, 15, 14, 12, 12, 11, 10][:FETCH_HOURS],
                   "precipitation_probability": probs,
                   "weather_code": [2, 3, 61, 61, 3, 3, 2, 2, 2, 1, 1, 1, 1][:FETCH_HOURS]},
        "daily": daily,
        "sun": _sun_events(daily, None),
    }


def _simulated_daily(rain_today: float, delta: dict) -> dict:
    today = {"temp": 8.0, "wind": 24.0, "rain": rain_today}
    tomorrow = {k: today[k] + delta[k] for k in today}
    tomorrow["rain"] = min(100.0, max(0.0, tomorrow["rain"]))
    tomorrow["wind"] = max(0.0, tomorrow["wind"])
    return {"temperature_2m_max": [today["temp"], tomorrow["temp"]],
            "wind_speed_10m_max": [today["wind"], tomorrow["wind"]],
            "precipitation_probability_max": [today["rain"], tomorrow["rain"]]}


def _request(lat: float, lon: float, config: dict, s: dict) -> dict:
    params = {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "current": "temperature_2m,apparent_temperature,wind_speed_10m,weather_code",
        "hourly": "temperature_2m,wind_speed_10m,precipitation_probability,weather_code",
        "forecast_hours": FETCH_HOURS,
        "daily": "temperature_2m_max,wind_speed_10m_max,precipitation_probability_max,sunrise,sunset",
        "forecast_days": 2,
        "timezone": config.get("timezone") or "UTC",
        "temperature_unit": s["temp_unit"],
        "wind_speed_unit": s["wind_unit"],
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "dashboard/0.1"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    if not isinstance(raw, dict) or raw.get("error"):
        raise RuntimeError(f"Open-Meteo error: {raw.get('reason') if isinstance(raw, dict) else raw}")

    # Hourly times are local wall times in the requested timezone; attach the
    # offset so they are unambiguous later.
    offset = timezone(timedelta(seconds=int(raw.get("utc_offset_seconds") or 0)))
    times = []
    for t in (raw.get("hourly") or {}).get("time") or []:
        try:
            times.append(datetime.fromisoformat(t).replace(tzinfo=offset).isoformat())
        except (TypeError, ValueError):
            times.append(None)
    daily = raw.get("daily") or {}
    return {"time": times, "current": raw.get("current") or {}, "hourly": raw.get("hourly") or {},
            "daily": daily, "sun": _sun_events(daily, offset)}


def _sun_events(daily: dict, offset) -> list[list[str]]:
    """[["sunrise" | "sunset", iso time], ...] in time order. Times without an
    offset get `offset` (None: they already carry one)."""
    out = []
    for kind in ("sunrise", "sunset"):
        for t in daily.get(kind) or []:
            try:
                dt = datetime.fromisoformat(t)
            except (TypeError, ValueError):
                continue
            if dt.tzinfo is None and offset is not None:
                dt = dt.replace(tzinfo=offset)
            out.append([kind, dt.isoformat()])
    return sorted(out, key=lambda e: e[1])


def fetch(config: dict) -> dict:
    s = _settings(config)
    simulate = bool(config.get("simulate"))
    lat, lon = config.get("latitude"), config.get("longitude")
    if not simulate and (_blank(lat) or _blank(lon)):
        return {"status": "needs_location"}

    if simulate:
        raw = _simulated(config, s)
    else:
        lat_f, lon_f = _num(lat), _num(lon)
        if lat_f is None or lon_f is None or not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
            raise ValueError("weather.latitude/longitude must be valid numbers")
        raw = _request(lat_f, lon_f, config, s)

    cur, hourly, times = raw["current"], raw["hourly"], raw["time"]
    temps = hourly.get("temperature_2m") or []
    codes = hourly.get("weather_code") or []
    probs = hourly.get("precipitation_probability") or []
    winds = hourly.get("wind_speed_10m") or []

    temp_now = _num(cur.get("temperature_2m"))
    if temp_now is None:
        temp_now = _num(_at(temps, 0))
    code_now = _num(cur.get("weather_code"))
    if code_now is None:
        code_now = _num(_at(codes, 0))

    # Peak precipitation probability over the current hour and the next 3.
    rain_max = rain_time = rain_index = None
    for i in range(HOURS_AHEAD + 1):
        p = _num(_at(probs, i))
        if p is not None and (rain_max is None or p > rain_max):
            rain_max, rain_time = p, _at(times, i)
            rain_index = i

    return {
        "status": "ok",
        "sample": simulate,
        "temp_now": temp_now,
        "feels_now": _num(cur.get("apparent_temperature")),
        "hourly": [{"time": _at(times, i), "temp": _num(_at(temps, i)), "rain": _num(_at(probs, i))}
                   for i in range(min(FETCH_HOURS, len(times)))],
        "sun": raw.get("sun") or [],
        "wind_later": _num(_at(winds, WIND_LATER_HOURS)),
        "code_now": None if code_now is None else int(code_now),
        "wind_now": _num(cur.get("wind_speed_10m")),
        "wind_unit": WIND_UNITS[s["wind_unit"]],
        "rain_max": rain_max,
        "rain_time": rain_time,
        "rain_is_now": rain_max is not None and rain_index == 0,
        "rain_threshold": s["threshold"],
        "tomorrow_tags": s["tomorrow_tags"],
        "wind_unit_key": s["wind_unit"],
        "daily": _daily_pair(raw.get("daily") or {}),
    }


# ----- layout --------------------------------------------------------------
def _round(x) -> int:
    return int(math.floor(x + 0.5))


def _deg(x) -> str:
    return f"{_round(x)}°"


def _daily_pair(daily: dict) -> dict | None:
    """{"temp": [today, tomorrow], "wind": [...], "rain": [...]}, or None if incomplete."""
    out = {}
    for key, name in (("temp", "temperature_2m_max"), ("wind", "wind_speed_10m_max"),
                      ("rain", "precipitation_probability_max")):
        vals = daily.get(name) or []
        pair = [_num(_at(vals, 0)), _num(_at(vals, 1))]
        out[key] = pair if None not in pair else None
    return out if any(out.values()) else None


def header_tags(data: dict, ctx) -> list[str]:
    """Short tags for what changes tomorrow, shown beside the date."""
    if data.get("status") != "ok" or not data.get("tomorrow_tags") or not data.get("daily"):
        return []
    d = data["daily"]
    tags = []
    if d.get("temp"):
        diff = d["temp"][1] - d["temp"][0]
        if diff >= TOMORROW_TEMP_DELTA:
            tags.append("warmer")
        elif diff <= -TOMORROW_TEMP_DELTA:
            tags.append("cooler")
    if d.get("wind"):
        step = TOMORROW_WIND_DELTA.get(data.get("wind_unit_key"), TOMORROW_WIND_DELTA["kmh"])
        diff = d["wind"][1] - d["wind"][0]
        if diff >= step:
            tags.append("windier")
        elif diff <= -step:
            tags.append("calmer")
    if d.get("rain"):
        today, tomorrow = d["rain"]
        threshold = data.get("rain_threshold", 20)
        if tomorrow - today >= TOMORROW_RAIN_DELTA and tomorrow >= threshold:
            tags.append("rainier")
        elif today - tomorrow >= TOMORROW_RAIN_DELTA and today >= threshold:
            tags.append("drier")
    return tags  # nothing changes -> no tags at all


def _next_sun(data: dict, ctx) -> dict | None:
    """Side row part for the next sunrise or sunset after now."""
    for kind, when in data.get("sun") or []:
        try:
            if to_datetime(when) > ctx.now:
                clock, ampm = ctx.format_time(when, "clock").split(" ")
                return {"icon": kind, "value": clock, "unit": ampm}
        except (TypeError, ValueError):
            continue
    return None


def _strip(data: dict, ctx) -> dict | None:
    """Hourly element: temperature line and rain chance bars."""
    points = []
    for i, h in enumerate(data.get("hourly") or []):
        if not h.get("time"):
            continue
        dt = to_datetime(h["time"]).astimezone(ctx.tz)
        label = ctx.format_time(dt, "hour_short")
        if i == 0 or dt.hour in (0, 12):
            label += "a" if dt.hour < 12 else "p"
        points.append({"label": label, "value": h.get("temp"), "bar": h.get("rain")})
    if len(points) < 2:
        return None
    return {"type": "hourly", "points": points, "value_suffix": "°", "mark_every": STRIP_MARK_EVERY,
            "bar_threshold": data.get("rain_threshold", 20)}


def layout(data: dict, ctx) -> list[dict]:
    if data.get("status") == "needs_location":
        return [{"type": "text", "text": "Weather: set location in config.yaml", "size": "small"}]

    temp_now = data.get("temp_now")
    code = data.get("code_now")
    wind, wind_later = data.get("wind_now"), data.get("wind_later")

    rain_max = data.get("rain_max")
    note = None
    if rain_max is not None and rain_max >= data.get("rain_threshold", 20):
        if data.get("rain_is_now") or not data.get("rain_time"):
            when = "now"
        else:
            when = f"by {ctx.format_time(data['rain_time'], 'hour')}"
        note = {"icon": "drop", "value": f"{_round(rain_max)}%", "caption": when}

    side = []
    if wind is not None:
        side.append({"icon": "wind", "value": str(_round(wind)),
                     "secondary": str(_round(wind_later)) if wind_later is not None else None,
                     "unit": data.get("wind_unit", "")})
    parts = []
    if data.get("feels_now") is not None:
        parts.append({"prefix": "feels", "value": _deg(data["feels_now"])})
    sun = _next_sun(data, ctx)
    if sun:
        parts.append(sun)
    if parts:
        side.append({"parts": parts, "size": 40})

    out = []
    if data.get("sample"):
        out.append({"type": "text", "text": "SAMPLE weather (simulate: true), not real",
                    "size": "small", "bold": True})
    # Big current temperature; condition icon with the rain chance under it
    # (only when rain reaches the threshold); on the right, wind, then
    # "feels like" and the next sunrise or sunset. Then the hourly strip.
    out.append({"type": "hero", "value": _deg(temp_now) if temp_now is not None else "--",
                "icon": condition_icon(code), "icon_alt": condition(code),
                "note": note, "side": side})
    strip = _strip(data, ctx)
    if strip:
        out += [{"type": "divider"}, strip]
    return out
