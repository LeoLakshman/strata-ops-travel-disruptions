"""
Stay & Highway Halt Advisory Service.
Generates strategic roadside halt suggestions (fatigue mitigation, EV charging, weather shelters)
and hotel/motel recommendations along interstate corridors for multi-day drives or emergency weather layovers.
"""

import logging
from typing import Dict, List, Optional
from app.models import HaltSuggestion, StayRecommendation

logger = logging.getLogger(__name__)


class StayService:
    @staticmethod
    def generate_halts_and_stays(
        origin: Dict,
        destination: Dict,
        driving_distance_miles: float,
        roadway_hazards: List[Dict],
        composite_risk_score: int,
    ) -> Dict[str, List]:
        """
        Generates tactical halt waypoints and vetted stay/motel recommendations
        geocoded along the route corridor.
        """
        orig_city = origin["city"]
        dest_city = destination["city"]
        orig_code = origin["iata"]
        dest_code = destination["iata"]

        halts: List[HaltSuggestion] = []
        stays: List[StayRecommendation] = []

        lat1, lon1 = origin["lat"], origin["lon"]
        lat2, lon2 = destination["lat"], destination["lon"]

        # =========================================================================
        # 1. HALT SUGGESTIONS (Rest stops, EV hubs, Weather staging)
        # =========================================================================
        # Stop 1: Early transit fatigue & fuel buffer (at ~20% of distance or 180 mi)
        dist_1 = round(min(180.0, driving_distance_miles * 0.25), 1)
        halts.append(HaltSuggestion(
            stop_number=1,
            stop_type="fuel_ev_hub",
            location_name=f"Corridor Gateway Service Plaza (Exiting {orig_city})",
            highway="Interstate Mainline",
            mile_marker="Exit 142 / MM 140",
            distance_from_origin_miles=dist_1,
            estimated_drive_time="2h 45m",
            rationale="Initial driver fatigue break, commercial vehicle tire pressure verification, and fuel/EV fast charging top-up.",
            facilities=["Tesla Supercharger / CCS EV Fast Charging", "24/7 Travel Plaza", "Commercial Truck Parking", "Hot Food"],
            lat=round(lat1 + (lat2 - lat1) * 0.22, 4),
            lon=round(lon1 + (lon2 - lon1) * 0.22, 4),
        ))

        # Stop 2: Midpoint Rest Stop & Weather Checkpoint
        dist_2 = round(driving_distance_miles * 0.50, 1)
        halts.append(HaltSuggestion(
            stop_number=2,
            stop_type="safe_haven_weather_shelter",
            location_name="Mid-Corridor Interstate Welcome & Inspection Center",
            highway="Interstate Mainline",
            mile_marker="MM 480",
            distance_from_origin_miles=dist_2,
            estimated_drive_time="7h 15m",
            rationale="Mandatory driver swap or rest break. Check updated DOT 511 highway pass status and local Doppler radar before proceeding.",
            facilities=["State DOT Weather Information Kiosk", "Restrooms", "Emergency Vehicle Assistance", "Picnic / Pet Relief"],
            lat=round(lat1 + (lat2 - lat1) * 0.50, 4),
            lon=round(lon1 + (lon2 - lon1) * 0.50, 4),
        ))

        # Stop 3: Pre-Hazard Mountain / Suburban Approach Staging
        dist_3 = round(max(dist_2 + 100.0, driving_distance_miles * 0.85), 1)
        halts.append(HaltSuggestion(
            stop_number=3,
            stop_type="rest_stop",
            location_name=f"Staging Area before {dest_city} Metro Approach",
            highway="Interstate Approach",
            mile_marker="Exit 38",
            distance_from_origin_miles=dist_3,
            estimated_drive_time="11h 30m" if driving_distance_miles > 600 else "4h 20m",
            rationale="Final halt before entering high-density metropolitan beltway or mountain gradient. Review live city rush-hour congestion.",
            facilities=["High-Speed Wi-Fi", "Coffee / Fuel", "Restrooms"],
            lat=round(lat1 + (lat2 - lat1) * 0.82, 4),
            lon=round(lon1 + (lon2 - lon1) * 0.82, 4),
        ))

        # =========================================================================
        # 2. STAY / MOTEL RECOMMENDATIONS (Strategic lodging along route)
        # =========================================================================
        
        # Stay 1: Mid-corridor Business Hotel (Primary Corporate Choice)
        stays.append(StayRecommendation(
            stay_id="stay_mid_corp",
            name="Courtyard by Marriott / Hampton Inn Mid-Corridor",
            location="Interstate Hub Central",
            highway_exit="Interstate Exit 210B",
            tier="business_hotel",
            price_tier="$$",
            strategic_role="Primary overnight rest stop for single-driver compliance (limits maximum daily driving to safe 8-hour window).",
            amenities=["High-Speed Corporate Wi-Fi", "24/7 Business Center", "Level 2 & DC Fast EV Charging", "Complimentary Hot Breakfast"],
            contingency_trigger="Scheduled overnight rest stop if drive exceeds 8 hours, or if darkness impairs driving conditions.",
            lat=round(lat1 + (lat2 - lat1) * 0.48 + 0.05, 4),
            lon=round(lon1 + (lon2 - lon1) * 0.48 - 0.05, 4),
        ))

        # Stay 2: Tactical Mountain / Storm Staging Refuge (Pre-Hazard Stay)
        stays.append(StayRecommendation(
            stay_id="stay_pre_hazard",
            name="Hilton Garden Inn / Best Western Mountain Gateway",
            location=f"Staging Junction (Approach to {dest_city})",
            highway_exit="Highway Exit 188",
            tier="emergency_shelter",
            price_tier="$$",
            strategic_role="Critical weather refuge positioned immediately before mountain elevation gain or severe weather corridor.",
            amenities=["Emergency Power Generator", "Fleet Heated Parking", "On-site Restaurant", "Snow Chains Available Nearby"],
            contingency_trigger="Execute immediate booking if DOT issues Chain Control R2/R3, road blizzard advisory, or if pass closed past 17:00.",
            lat=round(lat1 + (lat2 - lat1) * 0.80 + 0.08, 4),
            lon=round(lon1 + (lon2 - lon1) * 0.80 - 0.08, 4),
        ))

        # Stay 3: Budget Roadside Motel (Flexible / Quick Turnaround)
        stays.append(StayRecommendation(
            stay_id="stay_budget_express",
            name="Holiday Inn Express / Motel 6 Roadside Suites",
            location="Key Interchange Corridor",
            highway_exit="Interstate Exit 95",
            tier="budget_motel",
            price_tier="$",
            strategic_role="Cost-effective, rapid check-in roadside lodge ideal for solo technicians or short-notice emergency halts.",
            amenities=["Contactless 24/7 Check-in", "Free Truck/Van Parking", "Pet Friendly", "Grab & Go Coffee"],
            contingency_trigger="Deploy if unplanned highway traffic or unexpected maintenance requires an immediate 4-hour power nap.",
            lat=round(lat1 + (lat2 - lat1) * 0.65 - 0.05, 4),
            lon=round(lon1 + (lon2 - lon1) * 0.65 + 0.05, 4),
        ))

        return {
            "halts": halts,
            "stays": stays,
        }
