"""
FAA National Airspace System (NAS) Status Service.
Connects directly to the FAA Air Traffic Control System Command Center (ATCSCC)
to retrieve real-time Ground Stops, Ground Delay Programs (GDP), Arrival/Departure Delays,
and Airport Closures across the United States.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

FAA_STATUS_URL = "https://nasstatus.faa.gov/api/airport-status-information"
HTTP_TIMEOUT = 7.0
USER_AGENT = "TravelDisruptionAssessment/1.0 (ops-support@company.com)"


class FAAService:
    @staticmethod
    async def fetch_nas_status() -> Dict:
        """
        Retrieves and parses current FAA National Airspace System operational status.
        """
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            try:
                response = await client.get(
                    FAA_STATUS_URL,
                    headers={"User-Agent": USER_AGENT, "Accept": "application/xml, text/xml, */*"}
                )
                response.raise_for_status()
                return FAAService._parse_faa_xml(response.text)
            except Exception as e:
                logger.warning(f"Failed to fetch live FAA NAS status: {e}")
                return {
                    "available": False,
                    "error": str(e),
                    "update_time": None,
                    "ground_stops": [],
                    "ground_delays": [],
                    "arrival_departure_delays": [],
                    "closures": [],
                    "all_affected_airports": [],
                }

    @staticmethod
    def _parse_faa_xml(xml_content: str) -> Dict:
        root = ET.fromstring(xml_content)
        update_time = root.findtext("Update_Time", "Unknown")
        
        ground_stops = []
        ground_delays = []
        arrival_departure_delays = []
        closures = []
        affected_airports = set()

        for delay_type in root.findall(".//Delay_type"):
            type_name = (delay_type.findtext("Name") or "").strip()
            
            # 1. Ground Stop Programs
            if "Ground Stop" in type_name:
                for prog in delay_type.findall(".//Program"):
                    arpt = (prog.findtext("ARPT") or "").strip().upper()
                    if arpt:
                        affected_airports.add(arpt)
                        ground_stops.append({
                            "airport": arpt,
                            "program_type": "Ground Stop",
                            "reason": (prog.findtext("Reason") or "Unspecified").strip(),
                            "end_time": (prog.findtext("End_Time") or "").strip(),
                            "severity": "critical",
                            "severity_weight": 95,
                        })

            # 2. Ground Delay Programs (GDP)
            elif "Ground Delay" in type_name:
                for gd in delay_type.findall(".//Ground_Delay"):
                    arpt = (gd.findtext("ARPT") or "").strip().upper()
                    if arpt:
                        affected_airports.add(arpt)
                        avg_delay = (gd.findtext("Avg") or "").strip()
                        max_delay = (gd.findtext("Max") or "").strip()
                        ground_delays.append({
                            "airport": arpt,
                            "program_type": "Ground Delay Program",
                            "reason": (gd.findtext("Reason") or "Airspace volume/weather").strip(),
                            "avg_delay": avg_delay,
                            "max_delay": max_delay,
                            "severity": "high",
                            "severity_weight": 80,
                        })

            # 3. General Arrival/Departure Delays
            elif "Arrival/Departure" in type_name:
                for d in delay_type.findall(".//Delay"):
                    arpt = (d.findtext("ARPT") or "").strip().upper()
                    if arpt:
                        affected_airports.add(arpt)
                        reason = (d.findtext("Reason") or "Traffic management").strip()
                        arr_dep_el = d.find(".//Arrival_Departure")
                        delay_kind = arr_dep_el.get("Type", "General") if arr_dep_el is not None else "General"
                        min_time = arr_dep_el.findtext("Min", "") if arr_dep_el is not None else ""
                        max_time = arr_dep_el.findtext("Max", "") if arr_dep_el is not None else ""
                        trend = arr_dep_el.findtext("Trend", "Steady") if arr_dep_el is not None else "Steady"
                        
                        arrival_departure_delays.append({
                            "airport": arpt,
                            "program_type": f"{delay_kind} Delay",
                            "reason": reason,
                            "min_delay": min_time,
                            "max_delay": max_time,
                            "trend": trend,
                            "severity": "medium",
                            "severity_weight": 55,
                        })

            # 4. Airport Closures
            elif "Closure" in type_name:
                for cl in delay_type.findall(".//Airport"):
                    arpt = (cl.findtext("ARPT") or "").strip().upper()
                    if arpt:
                        affected_airports.add(arpt)
                        closures.append({
                            "airport": arpt,
                            "program_type": "Airport Closure/Restriction",
                            "reason": (cl.findtext("Reason") or "Closed by NOTAM").strip(),
                            "start": (cl.findtext("Start") or "").strip(),
                            "reopen": (cl.findtext("Reopen") or "").strip(),
                            "severity": "critical",
                            "severity_weight": 90,
                        })

        return {
            "available": True,
            "update_time": update_time,
            "ground_stops": ground_stops,
            "ground_delays": ground_delays,
            "arrival_departure_delays": arrival_departure_delays,
            "closures": closures,
            "all_affected_airports": sorted(list(affected_airports)),
        }

    @staticmethod
    def get_airport_faa_status(nas_status: Dict, airport_iata: str) -> Dict:
        """
        Filters NAS status for a specific airport (origin or destination).
        """
        code = airport_iata.upper()
        stops = [s for s in nas_status.get("ground_stops", []) if s["airport"] == code]
        gds = [g for g in nas_status.get("ground_delays", []) if g["airport"] == code]
        arr_deps = [a for a in nas_status.get("arrival_departure_delays", []) if a["airport"] == code]
        closures = [c for c in nas_status.get("closures", []) if c["airport"] == code]

        has_disruption = bool(stops or gds or arr_deps or closures)
        
        # Calculate airport severity score
        score = 0
        status_label = "NORMAL OPERATIONS"
        if stops:
            score = 95
            status_label = "GROUND STOP IN EFFECT"
        elif gds:
            score = 80
            status_label = "GROUND DELAY PROGRAM ACTIVE"
        elif arr_deps:
            score = 50
            status_label = "ARRIVAL/DEPARTURE DELAYS REPORTED"
        elif closures:
            score = 70
            status_label = "RESTRICTION / NOTAM CLOSURE"

        return {
            "airport": code,
            "has_disruption": has_disruption,
            "status_label": status_label,
            "score": score,
            "ground_stops": stops,
            "ground_delays": gds,
            "arrival_departure_delays": arr_deps,
            "closures": closures,
        }
