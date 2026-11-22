"""Weather section: current conditions and the next 3 hours from Open-Meteo.

Config (dashboards.today.weather in config.yaml):
    latitude, longitude      blank -> a "Set location in config.yaml" note
    temperature_unit         celsius | fahrenheit   (default celsius)
    wind_unit                kmh | ms | mph | kn    (default kmh)
    rain_threshold_percent   show the rain block at or above this (default 20)
    simulate                 true -> fake SAMPLE values, no network
    simulate_rain_percent    with simulate: peak rain chance to fake (default 40),
                             so both the rain shown and the dry look can be previewed

Data source: https://open-meteo.com/ (free, no key; attribution required).
"""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

FOOTER_NOTE = "Weather: Open-Meteo.com"

API_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 15
HOURS_AHEAD = 3

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
    return {"temp_unit": temp_unit, "wind_unit": wind_unit, "threshold": threshold,
            "sim_rain": sim_rain}


def _simulated(config: dict, s: dict) -> dict:
    tz = ZoneInfo(config.get("timezone") or "UTC")
    hour = datetime.now(tz).replace(minute=0, second=0, microsecond=0)
    # Peak at +2h; the other hours are lower, so the peak hour is unambiguous.
    peak = s["sim_rain"]
    probs = [round(peak * k) for k in (0.25, 0.6, 1.0, 0.75)]
    return {
        "time": [(hour + timedelta(hours=i)).isoformat() for i in range(HOURS_AHEAD + 1)],
        "current": {"temperature_2m": 7.2, "wind_speed_10m": 18.4, "weather_code": 2},
        "hourly": {"temperature_2m": [7.0, 6.4, 5.8, 5.1],
                   "precipitation_probability": probs,
                   "weather_code": [2, 3, 61, 61]},
    }


def _request(lat: float, lon: float, config: dict, s: dict) -> dict:
    params = {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "current": "temperature_2m,wind_speed_10m,weather_code",
        "hourly": "temperature_2m,precipitation_probability,weather_code",
        "forecast_hours": HOURS_AHEAD + 1,
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
    return {"time": times, "current": raw.get("current") or {}, "hourly": raw.get("hourly") or {}}


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
        "temp_later": _num(_at(temps, HOURS_AHEAD)),
        "code_now": None if code_now is None else int(code_now),
        "wind_now": _num(cur.get("wind_speed_10m")),
        "wind_unit": WIND_UNITS[s["wind_unit"]],
        "rain_max": rain_max,
        "rain_time": rain_time,
        "rain_is_now": rain_max is not None and rain_index == 0,
        "rain_threshold": s["threshold"],
    }


# ----- layout --------------------------------------------------------------
def _round(x) -> int:
    return int(math.floor(x + 0.5))


def _deg(x) -> str:
    return f"{_round(x)}°"


def layout(data: dict, ctx) -> list[dict]:
    if data.get("status") == "needs_location":
        return [{"type": "text", "text": "Weather: set location in config.yaml", "size": "small"}]

    temp_now, temp_later = data.get("temp_now"), data.get("temp_later")
    code = data.get("code_now")
    temp_block = {
        "icon": condition_icon(code),
        "icon_alt": condition(code),
        "value": _deg(temp_now) if temp_now is not None else "--",
        "secondary": _deg(temp_later) if temp_later is not None else None,
        "size": 92,
    }

    wind = data.get("wind_now")
    wind_block = {
        "icon": "wind",
        "icon_alt": "Wind",
        "value": str(_round(wind)) if wind is not None else "",
        "unit": data.get("wind_unit", ""),
        "size": 56,
        "hidden": wind is None,
    }

    rain_max = data.get("rain_max")
    show_rain = rain_max is not None and rain_max >= data.get("rain_threshold", 20)
    when = ""
    if show_rain:
        if data.get("rain_is_now") or not data.get("rain_time"):
            when = "now"
        else:
            when = f"by {ctx.format_time(data['rain_time'], 'hour')}"
    rain_block = {
        "icon": "drop",
        "icon_alt": "Chance of rain",
        "value": f"{_round(rain_max)}%" if show_rain else "",
        "caption": when,
        "size": 56,
        "hidden": not show_rain,
    }

    out = []
    if data.get("sample"):
        out.append({"type": "text", "text": "SAMPLE weather (simulate: true), not real",
                    "size": "small", "bold": True})
    out.append({"type": "stats", "blocks": [temp_block, wind_block, rain_block]})
    return out
