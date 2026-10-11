"""
High-Resolution Numerical Weather Forecast Service.
Integrates Open-Meteo Aviation & Atmospheric Models (HRRR/GFS/ECMWF blend)
to provide hourly forecast timelines, precipitation probabilities, wind gust profiles,
and en-route flight corridor weather.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HTTP_TIMEOUT = 7.0
USER_AGENT = "TravelDisruptionAssessment/1.0 (ops-support@company.com)"

# WMO Weather interpretation codes
WMO_CODE_MAP = {
    0: ("Clear sky", "low", 5),
    1: ("Mainly clear", "low", 10),
    2: ("Partly cloudy", "low", 15),
    3: ("Overcast", "low", 20),
    45: ("Fog", "medium", 55),
    48: ("Depositing rime fog", "high", 70),
    51: ("Light drizzle", "low", 25),
    53: ("Moderate drizzle", "medium", 35),
    55: ("Dense drizzle", "medium", 45),
    56: ("Light freezing drizzle", "high", 75),
    57: ("Dense freezing drizzle", "critical", 85),
    61: ("Slight rain", "low", 25),
    63: ("Moderate rain", "medium", 45),
    65: ("Heavy rain", "high", 70),
    66: ("Light freezing rain", "high", 80),
    67: ("Heavy freezing rain", "critical", 95),
    71: ("Slight snow fall", "medium", 50),
    73: ("Moderate snow fall", "high", 75),
    75: ("Heavy snow fall", "critical", 90),
    77: ("Snow grains", "medium", 40),
    80: ("Slight rain showers", "medium", 35),
    81: ("Moderate rain showers", "medium", 50),
    82: ("Violent rain showers", "high", 75),
    85: ("Slight snow showers", "medium", 55),
    86: ("Heavy snow showers", "critical", 85),
    95: ("Thunderstorm", "high", 85),
    96: ("Thunderstorm with slight hail", "critical", 92),
    99: ("Thunderstorm with heavy hail", "critical", 98),
}


class ForecastService:
    @staticmethod
    async def get_hourly_forecast(
        lat: float,
        lon: float,
        target_date_str: str = "tomorrow",
        timezone: str = "auto"
    ) -> Dict:
        """
        Retrieves hourly weather forecast for a location on the target travel date.
        """
        # Determine actual date
        today = date.today()
        if target_date_str == "today":
            target_date = today
        elif target_date_str == "tomorrow":
            target_date = today + timedelta(days=1)
        else:
            try:
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            except ValueError:
                target_date = today + timedelta(days=1)

        target_iso = target_date.strftime("%Y-%m-%d")

        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_gusts_10m,visibility",
            "timezone": timezone,
            "forecast_days": 7,
        }

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            try:
                resp = await client.get(
                    OPEN_METEO_FORECAST_URL,
                    params=params,
                    headers={"User-Agent": USER_AGENT}
                )
                resp.raise_for_status()
                data = resp.json()
                hourly = data.get("hourly", {})
                
                times = hourly.get("time", [])
                temps = hourly.get("temperature_2m", [])
                precip_probs = hourly.get("precipitation_probability", [])
                precips = hourly.get("precipitation", [])
                wcodes = hourly.get("weather_code", [])
                winds = hourly.get("wind_speed_10m", [])
                gusts = hourly.get("wind_gusts_10m", [])
                visibs = hourly.get("visibility", [])
                
                # Filter down to the target travel date
                timeline = []
                max_wind_gust = 0.0
                max_precip_prob = 0
                highest_wcode = 0
                highest_score = 0
                
                for i, t in enumerate(times):
                    if t.startswith(target_iso):
                        try:
                            hour_part = t.split("T")[1][:5]
                        except IndexError:
                            hour_part = t
                        
                        temp_c = temps[i] if i < len(temps) and temps[i] is not None else 20.0
                        temp_f = round(temp_c * 9/5 + 32, 1)
                        prob = precip_probs[i] if i < len(precip_probs) and precip_probs[i] is not None else 0
                        precip_mm = precips[i] if i < len(precips) and precips[i] is not None else 0.0
                        wcode = wcodes[i] if i < len(wcodes) and wcodes[i] is not None else 0
                        wspd_kmh = winds[i] if i < len(winds) and winds[i] is not None else 0.0
                        wspd_mph = round(wspd_kmh * 0.621371, 1)
                        gust_kmh = gusts[i] if i < len(gusts) and gusts[i] is not None else 0.0
                        gust_mph = round(gust_kmh * 0.621371, 1)
                        vis_m = visibs[i] if i < len(visibs) and visibs[i] is not None else 10000.0
                        vis_miles = round(vis_m / 1609.34, 1)
                        
                        desc, severity, score = WMO_CODE_MAP.get(wcode, ("Cloudy", "low", 20))
                        
                        # Extra score weight for strong wind gusts
                        if gust_mph >= 40:
                            score = max(score, 85)
                            severity = "critical"
                        elif gust_mph >= 30:
                            score = max(score, 65)
                            severity = "high"
                        elif gust_mph >= 22:
                            score = max(score, 45)
                            
                        # Extra score weight for high precipitation probability
                        if prob >= 70:
                            score = max(score, 60)
                            
                        if gust_mph > max_wind_gust:
                            max_wind_gust = gust_mph
                        if prob > max_precip_prob:
                            max_precip_prob = prob
                        if score > highest_score:
                            highest_score = score
                            highest_wcode = wcode

                        timeline.append({
                            "time": t,
                            "hour_label": hour_part,
                            "temp_c": round(temp_c, 1),
                            "temp_f": temp_f,
                            "precip_prob": prob,
                            "precip_mm": precip_mm,
                            "weather_code": wcode,
                            "weather_desc": desc,
                            "wind_speed_mph": wspd_mph,
                            "wind_gusts_mph": gust_mph,
                            "visibility_miles": vis_miles,
                            "severity": severity,
                            "disruption_score": score,
                        })

                primary_desc = WMO_CODE_MAP.get(highest_wcode, ("Fair", "low", 10))[0]

                return {
                    "available": True,
                    "target_date": target_iso,
                    "hourly_timeline": timeline,
                    "max_precip_prob": max_precip_prob,
                    "max_wind_gust_mph": max_wind_gust,
                    "highest_disruption_score": highest_score,
                    "predominant_hazard": primary_desc if highest_score >= 40 else "Benign Conditions",
                }
            except Exception as e:
                logger.warning(f"Failed to fetch forecast for ({lat}, {lon}): {e}")
                return {
                    "available": False,
                    "target_date": target_iso,
                    "hourly_timeline": [],
                    "max_precip_prob": 0,
                    "max_wind_gust_mph": 0.0,
                    "highest_disruption_score": 10,
                    "predominant_hazard": "Forecast unavailable",
                }
