from __future__ import annotations

from typing import TypeAlias

import requests
from flask import Flask, render_template, request

app = Flask(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 8

JsonObject: TypeAlias = dict[str, object]

WEATHER_CONDITIONS: dict[int, tuple[str, str]] = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Depositing rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Moderate drizzle", "🌦️"),
    55: ("Dense drizzle", "🌧️"),
    56: ("Light freezing drizzle", "🌧️"),
    57: ("Dense freezing drizzle", "🌧️"),
    61: ("Slight rain", "🌧️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    66: ("Light freezing rain", "🌧️"),
    67: ("Heavy freezing rain", "🌧️"),
    71: ("Slight snow", "🌨️"),
    73: ("Moderate snow", "🌨️"),
    75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "🌨️"),
    80: ("Slight rain showers", "🌦️"),
    81: ("Moderate rain showers", "🌧️"),
    82: ("Violent rain showers", "⛈️"),
    85: ("Slight snow showers", "🌨️"),
    86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with slight hail", "⛈️"),
    99: ("Thunderstorm with heavy hail", "⛈️"),
}


class WeatherServiceError(Exception):
    """Raised when the weather provider cannot return usable data."""


def _get_json(url: str, params: dict[str, str | int | float]) -> JsonObject:
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise WeatherServiceError("The weather service is temporarily unavailable.") from exc

    if not isinstance(data, dict):
        raise WeatherServiceError("The weather service returned an invalid response.")
    return data


def _number(data: JsonObject, key: str) -> int | float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WeatherServiceError("The weather service returned incomplete weather data.")
    return value


def fetch_weather(city: str) -> JsonObject | None:
    """Look up a city and return its current weather, or None if it was not found."""
    location_data = _get_json(
        GEOCODING_URL,
        {"name": city, "count": 1, "language": "en", "format": "json"},
    )
    locations = location_data.get("results")
    if not isinstance(locations, list) or not locations:
        return None

    location = locations[0]
    if not isinstance(location, dict):
        raise WeatherServiceError("The weather service returned an invalid location.")

    latitude = location.get("latitude")
    longitude = location.get("longitude")
    if (
        isinstance(latitude, bool)
        or not isinstance(latitude, (int, float))
        or isinstance(longitude, bool)
        or not isinstance(longitude, (int, float))
    ):
        raise WeatherServiceError("The weather service returned an invalid location.")

    weather_data = _get_json(
        WEATHER_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "is_day,precipitation,weather_code,wind_speed_10m"
            ),
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
        },
    )
    current = weather_data.get("current")
    if not isinstance(current, dict):
        raise WeatherServiceError("The weather service returned incomplete weather data.")

    weather_code = current.get("weather_code")
    if isinstance(weather_code, bool) or not isinstance(weather_code, int):
        raise WeatherServiceError("The weather service returned incomplete weather data.")
    condition, icon = WEATHER_CONDITIONS.get(weather_code, ("Unknown conditions", "🌡️"))

    location_parts = [
        location.get("name"),
        location.get("admin1"),
        location.get("country"),
    ]
    display_location = ", ".join(
        dict.fromkeys(part for part in location_parts if isinstance(part, str) and part)
    )

    return {
        "location": display_location or city,
        "temperature": _number(current, "temperature_2m"),
        "feels_like": _number(current, "apparent_temperature"),
        "humidity": _number(current, "relative_humidity_2m"),
        "precipitation": _number(current, "precipitation"),
        "wind_speed": _number(current, "wind_speed_10m"),
        "condition": condition,
        "icon": icon,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    city = ""
    weather = None
    error = None

    if request.method == "POST":
        city = request.form.get("city", "").strip()
        if not city:
            error = "Enter a city to see its current weather."
        elif len(city) > 100:
            error = "City names must be 100 characters or fewer."
        else:
            try:
                weather = fetch_weather(city)
                if weather is None:
                    error = f"We couldn't find “{city}”. Check the spelling and try again."
            except WeatherServiceError as exc:
                error = str(exc)

    return render_template("index.html", city=city, weather=weather, error=error)


if __name__ == "__main__":
    app.run()
