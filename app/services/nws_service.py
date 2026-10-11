"""
NOAA National Weather Service (NWS) Service.
Queries api.weather.gov for real-time active Weather Warnings, Watches, and Advisories
impacting departure airports, arrival airports, and surrounding metropolitan areas.
"""

import logging
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"
HTTP_TIMEOUT = 7.0
USER_AGENT = "TravelDisruptionAssessment/1.0 (ops-support@company.com)"


class NWSService:
    @staticmethod
    async def get_alerts_for_point(lat: float, lon: float, location_name: str = "") -> List[Dict]:
        """
        Retrieves active NWS weather alerts for a specific latitude and longitude point.
        """
        # Format lat,lon to 4 decimal places as recommended by weather.gov
        point_str = f"{round(lat, 4)},{round(lon, 4)}"
        url = f"{NWS_ALERTS_URL}?point={point_str}"
        
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            try:
                resp = await client.get(
                    url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "application/geo+json"
                    }
                )
                if resp.status_code == 404:
                    return []
                resp.raise_for_status()
                data = resp.json()
                features = data.get("features", [])
                
                parsed_alerts = []
                for f in features:
                    props = f.get("properties", {})
                    event = props.get("event", "Weather Alert")
                    severity = props.get("severity", "Unknown")
                    urgency = props.get("urgency", "Unknown")
                    certainty = props.get("certainty", "Unknown")
                    headline = props.get("headline") or f"{event} in effect"
                    description = props.get("description", "")
                    instruction = props.get("instruction", "")
                    
                    # Compute score based on severity & event type
                    score = NWSService._calculate_alert_score(event, severity, urgency)
                    
                    parsed_alerts.append({
                        "location": location_name,
                        "event": event,
                        "severity": severity.lower(),
                        "urgency": urgency.lower(),
                        "certainty": certainty.lower(),
                        "headline": headline,
                        "description": description[:400] + "..." if len(description) > 400 else description,
                        "instruction": instruction[:300] + "..." if len(instruction) > 300 else instruction,
                        "effective": props.get("effective"),
                        "expires": props.get("expires"),
                        "score": score,
                    })
                
                return parsed_alerts
            except Exception as e:
                logger.warning(f"Failed to fetch NWS alerts for ({lat}, {lon}): {e}")
                return []

    @staticmethod
    def _calculate_alert_score(event: str, severity: str, urgency: str) -> int:
        """
        Computes a 0-100 disruption score for a weather alert.
        """
        ev = event.lower()
        sev = severity.lower()
        
        # High-impact aviation events
        if any(term in ev for term in ["tornado", "blizzard", "hurricane", "ice storm", "derecho"]):
            return 95
        if any(term in ev for term in ["severe thunderstorm", "winter storm", "high wind", "gale", "freezing rain"]):
            return 80
        if any(term in ev for term in ["dense fog", "flood", "flash flood", "winter weather"]):
            return 60
        if any(term in ev for term in ["wind advisory", "frost", "freeze", "heat"]):
            return 35
            
        # General severity fallback
        if sev == "extreme":
            return 90
        elif sev == "severe":
            return 75
        elif sev == "moderate":
            return 50
        elif sev == "minor":
            return 25
        return 20
