"""
Roadway & Interstate Highway Corridor Service.
Analyzes U.S. highway travel corridors, driving distances, road weather hazards
(black ice, mountain pass chain controls, high-wind truck rollovers, heavy snow),
and highway traffic disruptions alongside airway travel.
"""

import logging
import math
from typing import Dict, List, Optional
from app.models import RoadwayDisruption

logger = logging.getLogger(__name__)

# Key US Interstate Highway Corridors connecting major metro hubs
HIGHWAY_CORRIDORS: Dict[str, List[str]] = {
    # Transcontinental & East-West
    "JFK-SFO": ["I-80 W (Lincoln Highway)", "I-76 W / I-70 W"],
    "EWR-SFO": ["I-80 W"],
    "ORD-BOS": ["I-90 E (Massachusetts Turnpike)", "I-80 E"],
    "ORD-JFK": ["I-80 E", "I-76 E (PA Turnpike)"],
    "DEN-SEA": ["I-25 N → I-80 W → I-84 W → I-82 W → I-90 W"],
    "LAX-LAS": ["I-15 N (Mojave Desert Corridor)"],
    "SFO-LAX": ["I-5 S (Central Valley) or US-101 S"],
    "DFW-LBB": ["I-20 W → US-84 W (Caprock Escarpment Route)"],
    "LBB-DFW": ["US-84 E → I-20 E"],
    # North-South
    "JFK-DCA": ["I-95 S (Northeast Megalopolis Corridor)"],
    "BOS-JFK": ["I-95 S / I-84 W / CT-15"],
    "ATL-MIA": ["I-75 S → Florida's Turnpike → I-95 S"],
    "DFW-IAH": ["I-45 S"],
    "SEA-SFO": ["I-5 S (Siskiyou Pass)"],
}

# State Highway & Regional Scenic Corridors
STATE_HIGHWAY_CORRIDORS: Dict[str, List[str]] = {
    "JFK-SFO": ["US-30 (Historic Lincoln Highway) / US-6 West (Toll-Free Scenic)"],
    "SFO-LAX": ["CA-1 (Pacific Coast Highway) / US-101 S (Coastal Corridor)"],
    "DFW-LBB": ["TX-114 W / US-380 W (State Highway Scenic Plains Corridor)"],
    "LAX-LAS": ["Historic Route 66 / CA-127 N (Desert State Route)"],
    "ORD-JFK": ["US-20 E / US-6 E (State Highway Byways)"],
}

# Weather-Optimized / Low-Elevation Bypasses
WEATHER_OPTIMIZED_CORRIDORS: Dict[str, List[str]] = {
    "JFK-SFO": ["I-40 W → CA-58 W (Southern Transcon Bypass — Avoids Donner Pass Snow Chains)"],
    "DEN-SEA": ["I-80 W → I-84 W (Low-Elevation Southern Bypass — Avoids Avalanche Mountain Passes)"],
    "SEA-SFO": ["US-101 S (Coastal Low-Elevation Bypass — Avoids Siskiyou Summit I-5 Black Ice)"],
}

# Critical Mountain Passes & High-Risk Highway Segments
MOUNTAIN_PASSES = [
    {"name": "Donner Pass (I-80)", "corridor": "I-80", "elev_ft": 7056, "state": "CA", "risk": "chain_control"},
    {"name": "Eisenhower-Johnson Tunnel / Loveland (I-70)", "corridor": "I-70", "elev_ft": 11158, "state": "CO", "risk": "snow_closure"},
    {"name": "Snoqualmie Pass (I-90)", "corridor": "I-90", "elev_ft": 3022, "state": "WA", "risk": "avalanche_control"},
    {"name": "Siskiyou Summit (I-5)", "corridor": "I-5", "elev_ft": 4310, "state": "OR-CA", "risk": "black_ice"},
    {"name": "El Cajon Pass (I-15)", "corridor": "I-15", "elev_ft": 3777, "state": "CA", "risk": "high_wind_overturn"},
]


class RoadwayService:
    @staticmethod
    def calculate_road_route(
        origin: Dict,
        destination: Dict,
        flight_distance_miles: float,
        highway_preference: str = "interstate"
    ) -> Dict:
        """
        Calculates realistic highway driving distance, durations, and waypoint route
        customized by user highway preference (Interstate vs State Highway vs Weather-Optimized).
        """
        pair_key1 = f"{origin['iata']}-{destination['iata']}"
        pair_key2 = f"{destination['iata']}-{origin['iata']}"

        # Adjust distance and speed profile based on highway preference
        if highway_preference == "state_highway":
            dist_multiplier = 1.28
            avg_speed_mph = 52.0
            interstates = STATE_HIGHWAY_CORRIDORS.get(pair_key1) or STATE_HIGHWAY_CORRIDORS.get(pair_key2) or [
                "State & Regional Highway Network (Toll-Free Scenic Corridor)"
            ]
        elif highway_preference == "weather_optimized":
            dist_multiplier = 1.25
            avg_speed_mph = 60.0
            interstates = WEATHER_OPTIMIZED_CORRIDORS.get(pair_key1) or WEATHER_OPTIMIZED_CORRIDORS.get(pair_key2) or [
                "Weather-Resilient Bypass Corridor (Bypasses High Mountain Snow Passes)"
            ]
        else: # "interstate"
            dist_multiplier = 1.18
            avg_speed_mph = 65.0
            interstates = HIGHWAY_CORRIDORS.get(pair_key1) or HIGHWAY_CORRIDORS.get(pair_key2) or [
                "Interstate Highway Network (I-80 / I-90 / I-40 / I-10 Transcon)"
            ]

        driving_distance = round(flight_distance_miles * dist_multiplier, 1)

        # Driving hours calculation
        pure_driving_hours = driving_distance / avg_speed_mph
        stops_count = int(pure_driving_hours // 3.5)
        total_hours = pure_driving_hours + (stops_count * 0.35)

        hours = int(total_hours)
        mins = int((total_hours - hours) * 60)
        drive_time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

        # Generate realistic highway waypoints along the route corridor
        lat1, lon1 = origin["lat"], origin["lon"]
        lat2, lon2 = destination["lat"], destination["lon"]
        waypoints = []
        num_pts = 6
        for i in range(num_pts + 1):
            f = i / num_pts
            # Subtle curvature simulating real highway corridor
            curvature = math.sin(math.pi * f) * (1.2 if highway_preference == "weather_optimized" else -0.5 if highway_preference == "state_highway" else 0.4)
            w_lat = round(lat1 + (lat2 - lat1) * f + curvature, 4)
            w_lon = round(lon1 + (lon2 - lon1) * f, 4)
            if i == 0:
                name = f"Origin: {origin['city']}"
            elif i == num_pts:
                name = f"Destination: {destination['city']}"
            else:
                name = f"Corridor Waypoint #{i} ({int(driving_distance * f)} mi)"
            waypoints.append({
                "name": name,
                "lat": w_lat,
                "lon": w_lon,
                "distance_from_origin": round(driving_distance * f, 1),
            })

        return {
            "driving_distance_miles": driving_distance,
            "driving_time_est": drive_time_str,
            "driving_hours": round(total_hours, 1),
            "primary_interstates": interstates,
            "highway_preference": highway_preference,
            "highway_waypoints": waypoints,
        }

    @staticmethod
    def assess_roadway_hazards(
        origin: Dict,
        destination: Dict,
        weather_origin: Dict,
        weather_dest: Dict,
        weather_midpoint: Dict,
    ) -> List[RoadwayDisruption]:
        """
        Analyzes road surface conditions, black ice probability, wind overturn risks,
        and mountain pass hazards along the interstate corridor.
        """
        disruptions: List[RoadwayDisruption] = []
        
        pair = f"{origin['iata']}-{destination['iata']}"
        interstate_name = HIGHWAY_CORRIDORS.get(pair, ["I-80 / Interstate System"])[0]

        # 1. High Wind Overturn Warning for commercial trucks / high-profile vehicles
        peak_wind = max(
            weather_origin.get("max_wind_gust_mph", 0),
            weather_dest.get("max_wind_gust_mph", 0),
            weather_midpoint.get("max_wind_gust_mph", 0),
        )
        if peak_wind >= 40:
            disruptions.append(RoadwayDisruption(
                highway=interstate_name,
                segment="Plains / Open Valley Interstate Exposures",
                condition_type="high_wind_warning",
                severity="high" if peak_wind >= 50 else "medium",
                delay_estimate_minutes=45,
                description=f"Crosswind gusts up to {peak_wind} mph detected along corridor. High-profile vehicles, vans, and commercial trucks face severe overturn hazard. Empty trailers restricted.",
                source="DOT Highway Weather Advisory",
            ))

        # 2. Black Ice / Freezing Road Surface Risk
        dest_temp = weather_dest.get("temp_c", 20.0)
        dest_precip = weather_dest.get("max_precip_prob", 0)
        if dest_temp <= 2.0 and dest_precip >= 30:
            disruptions.append(RoadwayDisruption(
                highway=interstate_name,
                segment=f"Metro Approach to {destination['city']}",
                condition_type="black_ice",
                severity="critical" if dest_temp <= 0.0 else "high",
                delay_estimate_minutes=60,
                description="Near-freezing surface temperatures combined with precipitation create imminent black ice risk across bridges, overpasses, and elevated flyovers.",
                source="State 511 Roadway Sensors",
            ))

        # 3. Mountain Pass Hazard (e.g. Sierra Nevada / Rockies / Cascades)
        if any(h in interstate_name for h in ["I-80", "I-70", "I-90", "I-5"]):
            if "I-80" in interstate_name and ("SFO" in pair or "RNO" in pair or "SMF" in pair):
                disruptions.append(RoadwayDisruption(
                    highway="I-80 West / East",
                    segment="Donner Pass (Elevation 7,056 ft)",
                    condition_type="chain_control",
                    severity="high" if dest_precip >= 40 else "medium",
                    delay_estimate_minutes=75,
                    description="High-altitude winter conditions: Caltrans Maximum Chain Control (R2/R3) frequently enforced during precipitation. Mandatory tire chain inspection checkpoint active.",
                    source="Caltrans District 3 / 511 Highway Status",
                ))
            elif "I-70" in interstate_name and ("DEN" in pair or "SLC" in pair):
                disruptions.append(RoadwayDisruption(
                    highway="I-70 West",
                    segment="Eisenhower Tunnel / Vail Pass (Elevation 11,158 ft)",
                    condition_type="blizzard",
                    severity="critical" if dest_precip >= 50 else "high",
                    delay_estimate_minutes=90,
                    description="Traction Law in effect for all passenger vehicles. Reduced visibility and steep gradients require emergency snow equipment.",
                    source="Colorado DOT (COTRIP)",
                ))

        # 4. Northeast Megalopolis Congestion & Road Delays
        if "I-95" in interstate_name and any(code in pair for code in ["JFK", "LGA", "EWR", "PHL", "BWI", "DCA", "BOS"]):
            disruptions.append(RoadwayDisruption(
                highway="I-95 Corridor",
                segment="Mid-Atlantic Urban Chokepoints",
                condition_type="congestion_toll_bottlenecks",
                severity="medium",
                delay_estimate_minutes=50,
                description="Heavy metropolitan volume, work zones, and toll plaza bottleneck delays. Road travel significantly slower than rail during peak commuter hours.",
                source="I-95 Corridor Coalition & NYSDOT",
            ))

        if not disruptions:
            disruptions.append(RoadwayDisruption(
                highway=interstate_name,
                segment="Main Interstate Route",
                condition_type="normal",
                severity="info",
                delay_estimate_minutes=0,
                description="Highway surfaces generally dry and clear. Standard interstate speed limits operable.",
                source="State DOT Travel Information",
            ))

        return disruptions
