"""
NOAA Aviation Weather Center (AWC) Service.
Retrieves real-time METAR observations, forward-looking Terminal Aerodrome Forecasts (TAF),
and active airborne SIGMET hazards (convective cells, severe turbulence, icing).
"""

import logging
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://aviationweather.gov/api/data"
HTTP_TIMEOUT = 7.0
USER_AGENT = "TravelDisruptionAssessment/1.0 (ops-support@company.com)"


class AviationWeatherService:
    @staticmethod
    async def get_metar(icao_ids: List[str]) -> Dict[str, Dict]:
        """
        Retrieves real-time METAR observations for a list of ICAO airport codes.
        """
        if not icao_ids:
            return {}
        
        ids_param = ",".join(icao_ids)
        url = f"{BASE_URL}/metar?ids={ids_param}&format=json"
        
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            try:
                resp = await client.get(url, headers={"User-Agent": USER_AGENT})
                resp.raise_for_status()
                data = resp.json()
                results = {}
                for item in data:
                    icao = item.get("icaoId", "").upper()
                    if icao:
                        results[icao] = AviationWeatherService._process_metar_item(item)
                return results
            except Exception as e:
                logger.warning(f"Failed to fetch METAR data for {icao_ids}: {e}")
                return {}

    @staticmethod
    def _process_metar_item(item: Dict) -> Dict:
        """
        Extracts structured aviation meteorological metrics from a raw METAR JSON record.
        """
        # Determine Flight Category: VFR, MVFR, IFR, LIFR
        flt_cat = item.get("fltCat") or item.get("fltcat")
        visib = item.get("visib")
        
        # Parse visibility float if possible
        visib_num = 10.0
        if visib is not None:
            try:
                visib_str = str(visib).replace("+", "").replace("<", "").strip()
                visib_num = float(visib_str)
            except ValueError:
                visib_num = 10.0

        # Calculate lowest ceiling (BKN or OVC)
        clouds = item.get("clouds") or item.get("cover") or []
        ceiling_ft = None
        if isinstance(clouds, list):
            for c in clouds:
                if isinstance(c, dict):
                    cov = c.get("cover", "")
                    base = c.get("base")
                    if cov in ("BKN", "OVC") and base is not None:
                        if ceiling_ft is None or base < ceiling_ft:
                            ceiling_ft = base

        # Fallback flight category calculation if not provided by API
        if not flt_cat:
            if (ceiling_ft is not None and ceiling_ft < 500) or visib_num < 1:
                flt_cat = "LIFR"
            elif (ceiling_ft is not None and ceiling_ft < 1000) or visib_num < 3:
                flt_cat = "IFR"
            elif (ceiling_ft is not None and ceiling_ft <= 3000) or visib_num <= 5:
                flt_cat = "MVFR"
            else:
                flt_cat = "VFR"

        # Severity mapping
        severity_map = {
            "LIFR": ("critical", 90, "Low Instrument Flight Rules (Dense Fog/Very Low Ceiling)"),
            "IFR": ("high", 75, "Instrument Flight Rules (Low Cloud/Reduced Visibility)"),
            "MVFR": ("medium", 45, "Marginal VFR (Reduced Ceiling or Haze/Rain)"),
            "VFR": ("low", 10, "Visual Flight Rules (Clear Sky / Normal Operations)"),
        }
        sev_info = severity_map.get(flt_cat, ("low", 15, "Normal Conditions"))

        wspd = item.get("wspd", 0) or 0
        wgst = item.get("wgst") or 0
        wx_string = item.get("wxString") or ""
        
        # Wind disruption flags
        wind_severity = "normal"
        if wgst >= 35 or wspd >= 30:
            wind_severity = "severe_crosswind"
        elif wgst >= 25 or wspd >= 20:
            wind_severity = "moderate_wind"

        obs_time = item.get("reportTime")
        if not obs_time and item.get("obsTime"):
            try:
                obs_time = str(item.get("obsTime"))
            except Exception:
                obs_time = None

        return {
            "icao": item.get("icaoId"),
            "name": item.get("name"),
            "flight_category": flt_cat,
            "category_desc": sev_info[2],
            "risk_severity": sev_info[0],
            "risk_score": sev_info[1],
            "raw_observation": item.get("rawOb", ""),
            "observation_time": obs_time,
            "temperature_c": item.get("temp"),
            "temperature_f": round(item.get("temp", 0) * 9/5 + 32, 1) if item.get("temp") is not None else None,
            "dewpoint_c": item.get("dewp"),
            "wind_dir_deg": item.get("wdir"),
            "wind_speed_kts": wspd,
            "wind_gust_kts": wgst if wgst > 0 else None,
            "wind_severity": wind_severity,
            "visibility_sm": visib_num,
            "ceiling_ft": ceiling_ft,
            "weather_phenomena": wx_string if wx_string else "Clear / No Significant Weather",
            "altimeter_inhg": item.get("altim"),
        }

    @staticmethod
    async def get_taf(icao_ids: List[str]) -> Dict[str, Dict]:
        """
        Retrieves Terminal Aerodrome Forecasts (TAF) for future disruption trajectory.
        """
        if not icao_ids:
            return {}
        
        ids_param = ",".join(icao_ids)
        url = f"{BASE_URL}/taf?ids={ids_param}&format=json"
        
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            try:
                resp = await client.get(url, headers={"User-Agent": USER_AGENT})
                resp.raise_for_status()
                data = resp.json()
                results = {}
                for item in data:
                    icao = item.get("icaoId", "").upper()
                    if icao:
                        results[icao] = {
                            "icao": icao,
                            "issue_time": item.get("issueTime"),
                            "valid_time_from": item.get("validTimeFrom"),
                            "valid_time_to": item.get("validTimeTo"),
                            "raw_taf": item.get("rawTAF", ""),
                            "remarks": item.get("remarks", ""),
                        }
                return results
            except Exception as e:
                logger.warning(f"Failed to fetch TAF data for {icao_ids}: {e}")
                return {}

    @staticmethod
    async def get_active_airsigmets() -> List[Dict]:
        """
        Retrieves active AIRMETs and SIGMETs for en-route flight corridors across the US.
        """
        url = f"{BASE_URL}/airsigmet?format=json"
        
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            try:
                resp = await client.get(url, headers={"User-Agent": USER_AGENT})
                resp.raise_for_status()
                data = resp.json()
                hazards = []
                for item in data:
                    hazard_type = item.get("hazard", "")
                    severity = item.get("severity")
                    raw = item.get("rawAirSigmet", "")
                    hazards.append({
                        "hazard": hazard_type,
                        "severity": severity,
                        "valid_time_from": item.get("validTimeFrom"),
                        "valid_time_to": item.get("validTimeTo"),
                        "altitude_min_ft": item.get("altitudeLow"),
                        "altitude_max_ft": item.get("altitudeHi"),
                        "raw_text": raw[:160] + "..." if len(raw) > 160 else raw,
                    })
                return hazards
            except Exception as e:
                logger.warning(f"Failed to fetch AIRSIGMET data: {e}")
                return []
