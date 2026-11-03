"""Settings in one place, so the city or the checks can be changed without touching the logic."""

CITY = "Munich"
LATITUDE = 48.137
LONGITUDE = 11.575
TIMEZONE = "Europe/Berlin"

AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_FIELDS = ["pm10", "pm2_5", "nitrogen_dioxide", "ozone"]
WEATHER_FIELDS = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precipitation", "visibility"]

# Extra weather values used only for the condition labels. They are stored but not
# run through the checks: 0 mm of rain repeated for hours is a dry spell, not a stuck sensor.
CONTEXT_FIELDS = ["precipitation", "visibility"]

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

# Real measuring stations. Umweltbundesamt (UBA) API, data from Bavaria's monitoring network.
# UBA times are always German winter time (UTC+1), all year round.
UBA_URL = "https://luftdaten.umweltbundesamt.de/api/air-data/v3/measures/json"
UBA_COMPONENTS = {1: "pm10", 3: "ozone", 5: "nitrogen_dioxide", 9: "pm2_5"}
STATION_FIELDS = ["pm10", "pm2_5", "nitrogen_dioxide", "ozone"]
STATIONS = {
    "DEBY039": {"id": 473, "name": "München/Lothstraße", "type": "urban background",
                "lat": 48.1545, "lon": 11.5547},
    "DEBY115": {"id": 535, "name": "München/Landshuter Allee", "type": "urban traffic",
                "lat": 48.1496, "lon": 11.5365},
}
# Stations report whole numbers, so at low levels the same value often repeats for hours.
# Six hours is too strict for them; twelve still catches a frozen sensor.
STATION_STUCK_HOURS = 12
# First day of the Open-Meteo history in the database, so the station history matches it.
STATION_HISTORY_START = "2026-10-17"

# Condition labels. These are my own working thresholds, not official definitions.
RAIN_MM = 0.5              # rain in the hour
STRONG_WIND_KMH = 40       # wind at 10 m
LOW_VISIBILITY_M = 1000    # fog
HAZE_PM25 = 25             # fine dust, µg/m³ ...
HAZE_HUMIDITY = 90         # ... in very humid air

DB_PATH = "data/air_quality.db"
DASHBOARD_JSON = "docs/data.json"
