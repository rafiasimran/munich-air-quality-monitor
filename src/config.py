"""Settings in one place, so the city or the checks can be changed without touching the logic."""

CITY = "Munich"
LATITUDE = 48.137
LONGITUDE = 11.575
TIMEZONE = "Europe/Berlin"

AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_FIELDS = ["pm10", "pm2_5", "nitrogen_dioxide", "ozone"]
WEATHER_FIELDS = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m"]

# Physically plausible ranges. Anything outside is almost certainly a data error.
VALID_RANGES = {
    "pm10": (0, 1000),
    "pm2_5": (0, 1000),
    "nitrogen_dioxide": (0, 1000),
    "ozone": (0, 800),
    "temperature_2m": (-40, 45),
    "relative_humidity_2m": (0, 100),
    "wind_speed_10m": (0, 200),
}

# Largest believable change from one hour to the next.
MAX_HOURLY_JUMP = {
    "pm10": 80,
    "pm2_5": 60,
    "nitrogen_dioxide": 80,
    "ozone": 60,
    "temperature_2m": 8,
    "relative_humidity_2m": 40,
    "wind_speed_10m": 40,
}

# The same value repeated this many hours in a row looks like a stuck sensor.
STUCK_HOURS = 6

# WHO 2021 air quality guidelines (24-hour mean, µg/m³).
WHO_DAILY_LIMITS = {"pm2_5": 15, "pm10": 45}

DB_PATH = "data/air_quality.db"
DASHBOARD_JSON = "docs/data.json"
