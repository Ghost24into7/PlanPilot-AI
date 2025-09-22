# weather.py
"""
Weather module.
Fetches forecast using Open-Meteo API (free, no key needed).
Handles geocoding and daily summaries.
"""

import requests
from datetime import datetime, timedelta

def get_weather(city: str, days: int = 7) -> str:
    """
    Get weather forecast for a city.
    :param city: City name.
    :param days: Number of days.
    :return: Formatted forecast string or None.
    """
    try:
        # Geocode
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        geo_resp = requests.get(geocode_url)
        if geo_resp.status_code != 200 or not geo_resp.json().get('results'):
            return None
        coords = geo_resp.json()['results'][0]
        lat, lon = coords['latitude'], coords['longitude']

        # Forecast
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=auto&forecast_days={days}"
        resp = requests.get(weather_url)
        if resp.status_code != 200:
            return None

        data = resp.json()['daily']
        forecast = []
        for i in range(days):
            date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            max_t = data['temperature_2m_max'][i]
            min_t = data['temperature_2m_min'][i]
            code = data['weathercode'][i]
            desc = {
                0: "Clear sky ☀️", 1: "Mainly clear 🌤️", 2: "Partly cloudy ⛅",
                3: "Overcast ☁️", 61: "Light rain 🌦️", 63: "Moderate rain 🌧️", 80: "Showers 🚿"
            }.get(code, "Unknown")
            forecast.append(f"{date}: {min_t}°C to {max_t}°C, {desc}")
        return "\n".join(forecast)
    except Exception:
        return None