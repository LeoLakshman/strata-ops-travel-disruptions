"""
Operational Rerouting & Alternate Route Advisory Service.
Analyzes co-terminal airport bypasses, connecting hub weather diversions,
and multimodal roadway alternatives to mitigate high-risk travel disruptions.
"""

import logging
from typing import Dict, List, Optional
from app.models import AlternateRouteSuggestion, RiskLevel

logger = logging.getLogger(__name__)

# Metro Area Co-Terminal Airport Networks
METRO_CO_TERMINALS: Dict[str, List[Dict[str, str]]] = {
    "San Francisco": [
        {"iata": "OAK", "name": "Oakland International Airport", "distance_to_core": "20 mi (BART directly to downtown SF)", "metro": "San Francisco"},
        {"iata": "SJC", "name": "San Jose Mineta International", "distance_to_core": "45 mi (Caltrain to SF)", "metro": "San Francisco"},
    ],
    "New York": [
        {"iata": "EWR", "name": "Newark Liberty International", "distance_to_core": "16 mi (NJ Transit to Penn Station)", "metro": "New York"},
        {"iata": "JFK", "name": "John F. Kennedy International", "distance_to_core": "18 mi (LIRR to Manhattan)", "metro": "New York"},
        {"iata": "LGA", "name": "LaGuardia Airport", "distance_to_core": "9 mi (Taxi/M60 SBS to Midtown)", "metro": "New York"},
        {"iata": "HPN", "name": "Westchester County Airport", "distance_to_core": "33 mi (Metro-North to Grand Central)", "metro": "New York"},
    ],
    "Chicago": [
        {"iata": "MDW", "name": "Chicago Midway International", "distance_to_core": "11 mi (CTA Orange Line to Loop)", "metro": "Chicago"},
        {"iata": "ORD", "name": "O'Hare International Airport", "distance_to_core": "18 mi (CTA Blue Line to Loop)", "metro": "Chicago"},
    ],
    "Washington DC": [
        {"iata": "BWI", "name": "Baltimore/Washington International", "distance_to_core": "32 mi (MARC/Amtrak to Union Station)", "metro": "Washington DC"},
        {"iata": "DCA", "name": "Ronald Reagan Washington National", "distance_to_core": "4 mi (Metro Blue/Yellow Line)", "metro": "Washington DC"},
        {"iata": "IAD", "name": "Washington Dulles International", "distance_to_core": "26 mi (Silver Line Metro)", "metro": "Washington DC"},
    ],
    "Los Angeles": [
        {"iata": "BUR", "name": "Hollywood Burbank Airport", "distance_to_core": "14 mi (Metrolink to Downtown LA)", "metro": "Los Angeles"},
        {"iata": "SNA", "name": "John Wayne Airport (Orange County)", "distance_to_core": "38 mi to Downtown LA", "metro": "Los Angeles"},
        {"iata": "ONT", "name": "Ontario International Airport", "distance_to_core": "38 mi to Inland Empire/LA", "metro": "Los Angeles"},
    ],
    "Miami": [
        {"iata": "FLL", "name": "Fort Lauderdale-Hollywood International", "distance_to_core": "28 mi (Brightline to Miami Central)", "metro": "Miami"},
        {"iata": "MIA", "name": "Miami International Airport", "distance_to_core": "7 mi (Metrorail to Downtown)", "metro": "Miami"},
    ],
    "Dallas": [
        {"iata": "DAL", "name": "Dallas Love Field", "distance_to_core": "6 mi (DART to Downtown Dallas)", "metro": "Dallas"},
        {"iata": "DFW", "name": "Dallas/Fort Worth International", "distance_to_core": "19 mi (TEXRail to Fort Worth / DART to Dallas)", "metro": "Dallas"},
    ],
    "Houston": [
        {"iata": "HOU", "name": "William P. Hobby Airport", "distance_to_core": "10 mi to Downtown Houston", "metro": "Houston"},
        {"iata": "IAH", "name": "George Bush Intercontinental", "distance_to_core": "22 mi to Downtown Houston", "metro": "Houston"},
    ],
}


class ReroutingService:
    @staticmethod
    def generate_alternate_routes(
        origin: Dict,
        destination: Dict,
        travel_mode: str,
        composite_risk_score: int,
        driving_distance_miles: float,
        flight_distance_miles: float,
        faa_dest: Dict,
        forecast_dest: Dict,
        roadway_hazards: List[Dict],
    ) -> List[AlternateRouteSuggestion]:
        """
        Dynamically analyzes and proposes vetted alternate routes, co-terminal bypasses,
        or multimodal options when travel disruption risk is identified.
        """
        alternates: List[AlternateRouteSuggestion] = []
        orig_code = origin.get("iata", "ORIG")
        dest_code = destination.get("iata", "DEST")
        orig_city = origin.get("city", "Origin City")
        dest_city = destination.get("city", "Destination City")
        dest_metro = destination.get("metro", dest_city)

        is_high_risk = composite_risk_score >= 45

        # =========================================================================
        # 1. AIR MODE ALTERNATIVES
        # =========================================================================
        if travel_mode in ("air", "multimodal"):
            # A. Destination Metro Co-Terminal Bypass
            co_terms = METRO_CO_TERMINALS.get(dest_metro, [])
            for alt in co_terms:
                if alt["iata"] != dest_code:
                    # Co-terminals usually avoid destination-specific ground stops (e.g., SFO -> OAK)
                    proj_score = max(15, int(composite_risk_score * 0.38)) if is_high_risk else 18
                    risk_reduction = max(0, composite_risk_score - proj_score)

                    alternates.append(AlternateRouteSuggestion(
                        route_id=f"alt_coterm_{alt['iata'].lower()}",
                        title=f"Fly into {alt['iata']} ({alt['name'].split()[0]}) instead of {dest_code}",
                        travel_mode="air",
                        origin_code=orig_code,
                        origin_name=origin.get("name", orig_city),
                        destination_code=alt["iata"],
                        destination_name=alt["name"],
                        via=None,
                        estimated_duration="Matches scheduled flight time",
                        projected_risk_score=proj_score,
                        projected_risk_level="LOW" if proj_score < 40 else "MODERATE",
                        risk_reduction_points=risk_reduction,
                        key_benefit=f"Bypasses localized terminal ground delays and runway slot programs at {dest_code}. {alt['distance_to_core']}.",
                        tradeoff=f"Requires ground transit ({alt['distance_to_core']}) into final destination.",
                        action_type="switch_route",
                    ))
                    break # Suggest primary top co-terminal

            # B. Multimodal Highway Driving Alternative (for trips under 500 driving miles)
            if driving_distance_miles <= 550 and driving_distance_miles > 30:
                hours = int(driving_distance_miles // 62)
                mins = int((driving_distance_miles % 62) / 62 * 60)
                drive_score = 20 if len(roadway_hazards) == 0 else min(45, composite_risk_score - 25)
                risk_reduction = max(0, composite_risk_score - drive_score)

                alternates.append(AlternateRouteSuggestion(
                    route_id="alt_multimodal_drive",
                    title=f"Direct Highway Drive via Interstate ({orig_city} → {dest_city})",
                    travel_mode="road",
                    origin_code=orig_code,
                    origin_name=f"{orig_city} Corporate HQ",
                    destination_code=dest_code,
                    destination_name=f"{dest_city} Destination",
                    via="Interstate Mainline",
                    estimated_duration=f"~{hours}h {mins}m driving",
                    projected_risk_score=drive_score,
                    projected_risk_level="LOW" if drive_score < 40 else "MODERATE",
                    risk_reduction_points=risk_reduction,
                    key_benefit="100% immune to FAA airport ground stops, airline cancellations, and TSA security queues. Immediate departure flexibility.",
                    tradeoff=f"Longer transit time (~{hours}h {mins}m) compared to flight cruising speed; driver rest halts required.",
                    action_type="multimodal",
                ))

            # C. Southern / Clear Skies Connecting Hub Bypass (for long flights)
            if flight_distance_miles > 800:
                connect_hub = "DFW" if dest_code != "DFW" and orig_code != "DFW" else "PHX"
                connect_name = "Dallas/Fort Worth" if connect_hub == "DFW" else "Phoenix Sky Harbor"
                proj_score = max(20, int(composite_risk_score * 0.45))
                risk_reduction = max(0, composite_risk_score - proj_score)

                alternates.append(AlternateRouteSuggestion(
                    route_id=f"alt_connect_{connect_hub.lower()}",
                    title=f"Connect via {connect_hub} ({connect_name}) • Weather Bypass",
                    travel_mode="air",
                    origin_code=orig_code,
                    origin_name=origin.get("name", orig_city),
                    destination_code=dest_code,
                    destination_name=destination.get("name", dest_city),
                    via=connect_hub,
                    estimated_duration="+1h 45m connection buffer",
                    projected_risk_score=proj_score,
                    projected_risk_level="LOW" if proj_score < 40 else "MODERATE",
                    risk_reduction_points=risk_reduction,
                    key_benefit=f"Routes around active convective storm systems and high-altitude jet stream turbulence via clear southern corridor ({connect_hub}).",
                    tradeoff="Requires 1 stop layover instead of nonstop direct routing.",
                    action_type="switch_route",
                ))

        # =========================================================================
        # 2. ROADWAY MODE ALTERNATIVES
        # =========================================================================
        elif travel_mode == "road":
            pair = f"{orig_code}-{dest_code}"

            if pair in ("DFW-LBB", "LBB-DFW"):
                # DFW-LBB Alternate 1: US-82 / US-287 Plains Bypass
                alternates.append(AlternateRouteSuggestion(
                    route_id="alt_road_us82",
                    title="Upper Plains Bypass (US-287 N → US-82 W via Wichita Falls & Guthrie)",
                    travel_mode="road",
                    origin_code=orig_code,
                    origin_name=orig_city,
                    destination_code=dest_code,
                    destination_name=dest_city,
                    via="US-287 / US-82",
                    estimated_duration="5h 15m (308 mi)",
                    projected_risk_score=15,
                    projected_risk_level="LOW",
                    risk_reduction_points=max(0, composite_risk_score - 15),
                    key_benefit="Bypasses I-20 metroplex rush hour and Caprock Escarpment mountain gradient. Flat agricultural highway with low traffic and high speed limit.",
                    tradeoff="+12 miles vs straight line; fewer urban service plazas between towns.",
                    action_type="switch_route",
                ))

                # DFW-LBB Alternate 2: Commercial Regional Jet Air Shuttle
                alternates.append(AlternateRouteSuggestion(
                    route_id="alt_road_fly",
                    title=f"Commercial Regional Flight ({orig_code} → {dest_code})",
                    travel_mode="air",
                    origin_code=orig_code,
                    origin_name=origin.get("name", orig_city),
                    destination_code=dest_code,
                    destination_name=destination.get("name", dest_city),
                    via=None,
                    estimated_duration="1h 12m flight time",
                    projected_risk_score=20,
                    projected_risk_level="LOW",
                    risk_reduction_points=max(0, composite_risk_score - 20),
                    key_benefit="Eliminates 5.5 hours of highway pavement driving, driver fatigue, and potential crosswind gusts.",
                    tradeoff="Requires commercial airline booking and standard airport security check-in.",
                    action_type="switch_route",
                ))
            else:
                # Generic Road Alternative: State Highway Scenic / Weather Resilient Bypass
                alternates.append(AlternateRouteSuggestion(
                    route_id="alt_road_weather_bypass",
                    title="Weather-Resilient Low-Elevation Bypass Route",
                    travel_mode="road",
                    origin_code=orig_code,
                    origin_name=orig_city,
                    destination_code=dest_code,
                    destination_name=dest_city,
                    via="Secondary Interstate / State Bypass",
                    estimated_duration=f"~{int(driving_distance_miles * 1.12 // 60)}h driving",
                    projected_risk_score=max(15, int(composite_risk_score * 0.5)),
                    projected_risk_level="LOW",
                    risk_reduction_points=max(0, int(composite_risk_score * 0.5)),
                    key_benefit="Bypasses high-elevation mountain passes and congested metropolitan beltways.",
                    tradeoff="Adds approximately 10-15% additional driving distance.",
                    action_type="switch_route",
                ))

        return alternates
