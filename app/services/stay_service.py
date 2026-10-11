"""
Stay & Highway Halt Advisory Service.
Generates strategic roadside halt suggestions focused on driver fatigue mitigation,
fuel/EV charging, and weather shelter in recognized major cities along interstate corridors.
Also recommends vetted hotel/motel accommodations for multi-day drives or emergency weather layovers.
"""

import logging
import math
from typing import Dict, List, Optional
from app.models import HaltSuggestion, StayRecommendation
from app.airports import AIRPORTS_DB

logger = logging.getLogger(__name__)

# Curated Major Corridor Intermediate Cities & Travel Hubs
# Ordered sequentially from Origin to Destination along primary Interstate corridors.
CORRIDOR_MAJOR_CITIES: Dict[str, List[Dict]] = {
    "DFW-LBB": [
        {
            "city": "Weatherford", "state": "TX", "lat": 32.7593, "lon": -97.7972,
            "highway": "I-20 West", "exit": "Exit 408",
            "distance_ratio": 0.20,
            "location_name": "Weatherford Interstate Travel Plaza (I-20 W)",
            "stop_type": "fuel_ev_hub",
            "facilities": ["Tesla Supercharger (250kW)", "Love's Travel Stop", "24/7 Dining", "Commercial Truck Parking"],
            "rationale": "Early corridor checkpoint: verify tire pressures and top off fuel before rural West Texas segment.",
        },
        {
            "city": "Abilene", "state": "TX", "lat": 32.4487, "lon": -99.7331,
            "highway": "I-20 West", "exit": "Exit 286 (Junction US-84 / US-83)",
            "distance_ratio": 0.58,
            "location_name": "Abilene Major Hub & Interstate Gateway Plaza",
            "stop_type": "rest_stop",
            "facilities": ["Tesla Supercharger & Electrify America", "Pilot Flying J / Love's", "Hendrick Health Level 1 Center", "Full Dining"],
            "rationale": "Primary Recommended Halt (~2h 45m drive): Essential driver focus reset and refueling at West Texas's primary hub before the Caprock Escarpment ascent into Lubbock.",
        },
        {
            "city": "Sweetwater", "state": "TX", "lat": 32.4709, "lon": -100.4059,
            "highway": "I-20 West", "exit": "Exit 244",
            "distance_ratio": 0.70,
            "location_name": "Sweetwater Energy Corridor Travel Center",
            "stop_type": "fuel_ev_hub",
            "facilities": ["24/7 Travel Plaza", "Fast Food", "Restrooms", "Wind Turbine Scenic Overlook"],
            "rationale": "Secondary fatigue break: quick rest and wind conditions check across Nolan County plains.",
        },
        {
            "city": "Snyder", "state": "TX", "lat": 32.7179, "lon": -100.9176,
            "highway": "US-84 West", "exit": "Coliseum Ave Junction",
            "distance_ratio": 0.78,
            "location_name": "Snyder US-84 Commercial Service Center",
            "stop_type": "rest_stop",
            "facilities": ["Allsup's / Stripes Travel Center", "EV Level 2", "Restrooms", "Hot Food"],
            "rationale": "Final beverage and staging halt before entering Lubbock county.",
        },
    ],
    "LBB-DFW": [
        {
            "city": "Snyder", "state": "TX", "lat": 32.7179, "lon": -100.9176,
            "highway": "US-84 East", "exit": "Coliseum Ave Junction",
            "distance_ratio": 0.22,
            "location_name": "Snyder US-84 Commercial Service Center",
            "stop_type": "fuel_ev_hub",
            "facilities": ["Allsup's / Stripes Travel Center", "EV Level 2", "Restrooms", "Hot Food"],
            "rationale": "Base of Caprock break: quick tire and weather check after descending from the South Plains.",
        },
        {
            "city": "Abilene", "state": "TX", "lat": 32.4487, "lon": -99.7331,
            "highway": "I-20 East", "exit": "Exit 286 (Junction US-84 / US-83)",
            "distance_ratio": 0.42,
            "location_name": "Abilene Major Hub & Interstate Interchange",
            "stop_type": "rest_stop",
            "facilities": ["Tesla Supercharger & Electrify America", "Pilot Flying J / Love's", "Full Dining & Restrooms"],
            "rationale": "Primary Recommended Halt (~2h drive): West Texas commercial hub for driver fatigue reset, full meal, and merger onto I-20 East toward Dallas-Fort Worth.",
        },
        {
            "city": "Weatherford", "state": "TX", "lat": 32.7593, "lon": -97.7972,
            "highway": "I-20 East", "exit": "Exit 408",
            "distance_ratio": 0.80,
            "location_name": "Weatherford Interstate Gateway (I-20 E)",
            "stop_type": "rest_stop",
            "facilities": ["Buc-ee's / Pilot Travel Center", "Tesla Supercharger", "Restrooms", "Traffic Information Kiosk"],
            "rationale": "Final staging halt before entering Dallas-Fort Worth metropolitan loop rush hour.",
        },
    ],
    "LAX-LAS": [
        {
            "city": "Victorville", "state": "CA", "lat": 34.5362, "lon": -117.2928,
            "highway": "I-15 North", "exit": "Exit 153A (Bear Valley Rd)",
            "distance_ratio": 0.32,
            "location_name": "Victorville High Desert Gateway (I-15 N)",
            "stop_type": "fuel_ev_hub",
            "facilities": ["Tesla Supercharger", "24/7 Travel Centers", "Food & Restrooms"],
            "rationale": "Post-Cajon Pass inspection: check engine temp and tire pressure after 3,777 ft mountain climb.",
        },
        {
            "city": "Barstow", "state": "CA", "lat": 34.8958, "lon": -117.0173,
            "highway": "I-15 North", "exit": "Exit 184 (Main St / Historic Route 66)",
            "distance_ratio": 0.50,
            "location_name": "Barstow Mojave Crossroads & Station",
            "stop_type": "rest_stop",
            "facilities": ["Tesla Supercharger (V3 250kW)", "Barstow Station / In-N-Out", "Pilot Travel Center"],
            "rationale": "Primary Recommended Halt (~2h drive): Desert midway stop before the 115-mile open desert stretch to Nevada.",
        },
        {
            "city": "Baker", "state": "CA", "lat": 35.2638, "lon": -116.0744,
            "highway": "I-15 North", "exit": "Exit 245 (World's Tallest Thermometer)",
            "distance_ratio": 0.72,
            "location_name": "Baker Desert Oasis & Gateway Plaza",
            "stop_type": "fuel_ev_hub",
            "facilities": ["EV DC Fast Charging", "24/7 Fuel", "Greek / Fast Food", "Restrooms"],
            "rationale": "Pre-Mountain Pass buffer: check radiator coolant and AC before the steep Mountain Pass grade.",
        },
    ],
    "SFO-LAX": [
        {
            "city": "Los Banos", "state": "CA", "lat": 37.0583, "lon": -120.8500,
            "highway": "I-5 South", "exit": "Exit 403 (CA-152 Junction)",
            "distance_ratio": 0.30,
            "location_name": "Los Banos Central Valley Gateway",
            "stop_type": "fuel_ev_hub",
            "facilities": ["Tesla Supercharger", "Pacheco Pass Staging", "24/7 Dining"],
            "rationale": "Early Valley halt: rest after Pacheco Pass crossing before long Central Valley straightaway.",
        },
        {
            "city": "Kettleman City", "state": "CA", "lat": 35.9816, "lon": -119.9615,
            "highway": "I-5 South", "exit": "Exit 309 (CA-41 Junction)",
            "distance_ratio": 0.52,
            "location_name": "Kettleman City Major Megawatt Supercharger Plaza",
            "stop_type": "rest_stop",
            "facilities": ["Tesla Megawatt Lounge & Superchargers", "In-N-Out / Bravo Farms", "24/7 Fuel"],
            "rationale": "Primary Recommended Halt (~2h 45m drive): The premier I-5 midway stop for full driver recharge and vehicle energy top-off.",
        },
        {
            "city": "Tejon Ranch / Lebec", "state": "CA", "lat": 34.8789, "lon": -118.8872,
            "highway": "I-5 South", "exit": "Exit 219 (Outlets at Tejon)",
            "distance_ratio": 0.78,
            "location_name": "Tejon Pass Gateway & Mountain Staging",
            "stop_type": "safe_haven_weather_shelter",
            "facilities": ["Outlets Dining", "Tesla Supercharger", "CHP Mountain Weather Station"],
            "rationale": "Pre-Grapevine staging: check Caltrans Tejon Pass snow and high-wind camera status before ascending 4,144 ft summit.",
        },
    ],
    "JFK-DCA": [
        {
            "city": "Edison / New Brunswick", "state": "NJ", "lat": 40.5187, "lon": -74.4121,
            "highway": "NJ Turnpike / I-95 S", "exit": "Turnpike Exit 9 (Joyce Kilmer Plaza)",
            "distance_ratio": 0.25,
            "location_name": "Joyce Kilmer Travel Service Area",
            "stop_type": "fuel_ev_hub",
            "facilities": ["EV Fast Chargers", "Turnpike Dining Plaza", "Restrooms"],
            "rationale": "Exiting New York Metro: early break after clearing Staten Island / Manhattan bridges.",
        },
        {
            "city": "Wilmington / Newark", "state": "DE", "lat": 39.6837, "lon": -75.7497,
            "highway": "I-95 South", "exit": "Delaware Welcome Center (MM 5)",
            "distance_ratio": 0.55,
            "location_name": "Delaware I-95 Megalopolis Welcome Center",
            "stop_type": "rest_stop",
            "facilities": ["State Welcome Center", "EV Superchargers", "Starbucks & Food Court", "24/7 Restrooms"],
            "rationale": "Primary Recommended Halt (~2h 10m drive): Strategic mid-corridor halt avoiding toll plaza congestion.",
        },
        {
            "city": "Baltimore", "state": "MD", "lat": 39.2904, "lon": -76.6122,
            "highway": "I-95 South", "exit": "Exit 53 (Fort McHenry Approach)",
            "distance_ratio": 0.80,
            "location_name": "Maryland Travel Staging Center",
            "stop_type": "rest_stop",
            "facilities": ["Fuel / EV", "Traffic Advisory Kiosk", "Restrooms"],
            "rationale": "Pre-DC beltway staging: check live I-495 Capital Beltway delays.",
        },
    ],
    "ORD-BOS": [
        {
            "city": "Toledo", "state": "OH", "lat": 41.6528, "lon": -83.5379,
            "highway": "I-80 / I-90 East (Ohio Turnpike)", "exit": "Turnpike MM 76",
            "distance_ratio": 0.25,
            "location_name": "Fallen Timbers Ohio Service Plaza",
            "stop_type": "fuel_ev_hub",
            "facilities": ["EV Fast Charging", "24/7 Turnpike Dining", "Restrooms"],
            "rationale": "Driver fatigue reset after clearing Greater Chicago and Indiana toll road.",
        },
        {
            "city": "Cleveland", "state": "OH", "lat": 41.4993, "lon": -81.6944,
            "highway": "I-90 East", "exit": "Exit 173",
            "distance_ratio": 0.40,
            "location_name": "Greater Cleveland Interstate Travel Hub",
            "stop_type": "rest_stop",
            "facilities": ["Superchargers", "Travel Plazas", "Hospital Facilities"],
            "rationale": "Mid-Midwest hub: full meal halt and Lake Erie lake-effect snow radar check.",
        },
        {
            "city": "Buffalo / Erie", "state": "NY", "lat": 42.8864, "lon": -78.8784,
            "highway": "I-90 East (NYS Thruway)", "exit": "Thruway Exit 53",
            "distance_ratio": 0.60,
            "location_name": "Seneca Service Area (NYS Thruway)",
            "stop_type": "rest_stop",
            "facilities": ["Taste NY Food", "EV Fast Charging", "Restrooms"],
            "rationale": "Thruway break: check Western New York winter squall advisories.",
        },
        {
            "city": "Albany", "state": "NY", "lat": 42.6526, "lon": -73.7562,
            "highway": "I-90 East (Berkshire Section)", "exit": "Thruway Exit 24",
            "distance_ratio": 0.82,
            "location_name": "Capital District Gateway Staging",
            "stop_type": "safe_haven_weather_shelter",
            "facilities": ["EV Charging", "Food Plaza", "Berkshires Weather Cam"],
            "rationale": "Pre-Berkshire Mountain staging before ascending Massachusetts Turnpike.",
        },
    ],
    "DFW-IAH": [
        {
            "city": "Corsicana", "state": "TX", "lat": 32.0954, "lon": -96.4689,
            "highway": "I-45 South", "exit": "Exit 229",
            "distance_ratio": 0.28,
            "location_name": "Corsicana Interstate Travel Center",
            "stop_type": "fuel_ev_hub",
            "facilities": ["Collin Street Bakery", "EV Charging", "Fuel & Food"],
            "rationale": "Early transit pause after exiting Dallas-Fort Worth metroplex.",
        },
        {
            "city": "Madisonville", "state": "TX", "lat": 30.9499, "lon": -95.9119,
            "highway": "I-45 South", "exit": "Exit 142 (Buc-ee's Madisonville)",
            "distance_ratio": 0.58,
            "location_name": "Buc-ee's Madisonville Mega Travel Center",
            "stop_type": "rest_stop",
            "facilities": ["Buc-ee's (96 Fuel Pumps)", "Tesla Supercharger & CCS", "World-Class Clean Restrooms", "Full Texas BBQ"],
            "rationale": "Primary Recommended Halt (~2h drive): Premier halfway stop between Dallas and Houston for driver refreshment and vehicle refueling.",
        },
        {
            "city": "Huntsville", "state": "TX", "lat": 30.7235, "lon": -95.5508,
            "highway": "I-45 South", "exit": "Exit 114",
            "distance_ratio": 0.75,
            "location_name": "Sam Houston Forest Travel Plaza",
            "stop_type": "rest_stop",
            "facilities": ["EV Fast Charging", "24/7 Dining", "Restrooms"],
            "rationale": "Staging break before Houston Grand Parkway and I-610 Loop commuter traffic.",
        },
    ],
}


class StayService:
    @staticmethod
    def generate_halts_and_stays(
        origin: Dict,
        destination: Dict,
        driving_distance_miles: float,
        roadway_hazards: List[Dict],
        composite_risk_score: int,
        driving_hours: float = 0.0,
        desired_halt_count: Optional[int] = None,
        highway_preference: str = "interstate",
    ) -> Dict[str, List]:
        """
        Generates tactical halt waypoints situated in recognized major cities,
        calibrated to 2.5-3 hour driving intervals or user preference,
        alongside vetted corporate lodging recommendations.
        """
        orig_city = origin.get("city", "Origin City")
        dest_city = destination.get("city", "Destination City")
        orig_code = origin.get("iata", "ORIG")
        dest_code = destination.get("iata", "DEST")

        lat1, lon1 = origin["lat"], origin["lon"]
        lat2, lon2 = destination["lat"], destination["lon"]

        pair_key = f"{orig_code}-{dest_code}"

        # -------------------------------------------------------------------------
        # 1. Determine Target Number of Halts
        # -------------------------------------------------------------------------
        # If user explicitly requested halt count:
        if desired_halt_count is not None:
            num_halts = max(0, min(5, desired_halt_count))
        else:
            # Auto-calculation based on DOT/NHTSA driver alertness rule:
            # 1 halt roughly every 2.5 - 3.0 hours of driving
            if driving_hours <= 2.75:
                num_halts = 0
            elif driving_hours <= 6.0:
                # e.g., DFW to LBB (~4.8 - 5.5 hours): exactly 1 halt in a major city like Abilene
                num_halts = 1
            elif driving_hours <= 9.0:
                num_halts = 2
            elif driving_hours <= 12.5:
                num_halts = 3
            else:
                num_halts = 4

        # -------------------------------------------------------------------------
        # 2. Select Halts in Major Cities
        # -------------------------------------------------------------------------
        halts: List[HaltSuggestion] = []

        if num_halts > 0:
            curated_list = CORRIDOR_MAJOR_CITIES.get(pair_key)
            selected_raw = []

            if curated_list and len(curated_list) > 0:
                if num_halts == 1:
                    # Pick the primary mid-point major city (ratio closest to 0.50-0.58)
                    best = min(curated_list, key=lambda c: abs(c.get("distance_ratio", 0.5) - 0.55))
                    selected_raw = [best]
                elif num_halts == 2:
                    if len(curated_list) >= 2:
                        # Pick early-mid and late-mid
                        selected_raw = [curated_list[0], curated_list[-1] if len(curated_list) == 2 else curated_list[1]]
                    else:
                        selected_raw = curated_list[:2]
                elif num_halts >= 3:
                    selected_raw = curated_list[:num_halts]
            else:
                # Dynamic Major City Fallback for arbitrary pairs
                # Find real major cities/airports along the vector
                for i in range(num_halts):
                    target_ratio = (i + 1) / (num_halts + 1)
                    t_lat = lat1 + (lat2 - lat1) * target_ratio
                    t_lon = lon1 + (lon2 - lon1) * target_ratio

                    # Find closest city in AIRPORTS_DB with commercial presence
                    best_city = None
                    min_dist = 999999.0
                    for code, apt in AIRPORTS_DB.items():
                        d_lat = apt["lat"] - t_lat
                        d_lon = apt["lon"] - t_lon
                        deg_dist = math.sqrt(d_lat * d_lat + d_lon * d_lon)
                        if deg_dist < min_dist:
                            min_dist = deg_dist
                            best_city = apt

                    c_name = best_city["city"] if best_city else f"Corridor Hub #{i+1}"
                    c_state = best_city["state"] if best_city else ""
                    selected_raw.append({
                        "city": c_name,
                        "state": c_state,
                        "lat": best_city["lat"] if best_city else round(t_lat, 4),
                        "lon": best_city["lon"] if best_city else round(t_lon, 4),
                        "highway": "Interstate Corridor",
                        "exit": f"Exit {int(target_ratio * 200)}",
                        "distance_ratio": target_ratio,
                        "location_name": f"{c_name} Interstate Gateway Plaza",
                        "stop_type": "rest_stop" if i % 2 == 1 else "fuel_ev_hub",
                        "facilities": ["Tesla Supercharger / DC Fast EV", "24/7 Travel Plaza", "Food & Restrooms"],
                        "rationale": f"Strategic driver fatigue mitigation stop in {c_name} (interval ~{round(driving_hours * target_ratio, 1)}h elapsed).",
                    })

            # Build HaltSuggestion models
            for idx, raw in enumerate(selected_raw):
                dist_ratio = raw.get("distance_ratio", (idx + 1) / (num_halts + 1))
                dist_mi = round(driving_distance_miles * dist_ratio, 1)
                elapsed_hrs = (driving_hours * dist_ratio)
                eh = int(elapsed_hrs)
                em = int((elapsed_hrs - eh) * 60)
                time_str = f"{eh}h {em}m" if eh > 0 else f"{em}m"

                halts.append(HaltSuggestion(
                    stop_number=idx + 1,
                    stop_type=raw.get("stop_type", "rest_stop"),
                    location_name=raw["location_name"],
                    city=raw.get("city"),
                    state=raw.get("state"),
                    highway=raw.get("highway", "Interstate"),
                    mile_marker=raw.get("exit", "MM Transit"),
                    distance_from_origin_miles=dist_mi,
                    estimated_drive_time=time_str,
                    rationale=raw["rationale"],
                    facilities=raw.get("facilities", ["Fuel", "Restrooms", "Food"]),
                    lat=raw.get("lat"),
                    lon=raw.get("lon"),
                ))

        # -------------------------------------------------------------------------
        # 3. STAY / HOTEL RECOMMENDATIONS (Anchored to Major Route Cities)
        # -------------------------------------------------------------------------
        stays: List[StayRecommendation] = []

        # If a recognized halt city exists, anchor the primary stay to that major city!
        anchor_city = halts[0].city if halts and halts[0].city else "Mid-Corridor Hub"
        anchor_state = halts[0].state if halts and halts[0].state else ""
        anchor_label = f"{anchor_city}, {anchor_state}" if anchor_state else anchor_city

        # Stay 1: Mid-corridor Business Hotel
        stays.append(StayRecommendation(
            stay_id="stay_mid_corp",
            name=f"Courtyard by Marriott / Hampton Inn ({anchor_city})",
            location=f"{anchor_label} • Interstate Commercial Hub",
            highway_exit="Interstate Mainline Exit",
            tier="business_hotel",
            price_tier="$$",
            strategic_role=f"Primary corporate lodging in {anchor_city} to enforce single-driver rest compliance and avoid nighttime driving fatigue.",
            amenities=["High-Speed Corporate Wi-Fi", "Level 2 & DC Fast EV Charging", "24/7 Business Center", "Hot Breakfast"],
            contingency_trigger="Scheduled overnight rest stop if trip exceeds safe 8-hour driving window or severe storm conditions worsen.",
            lat=round(halts[0].lat + 0.02, 4) if halts and halts[0].lat else round(lat1 + (lat2 - lat1) * 0.50, 4),
            lon=round(halts[0].lon - 0.02, 4) if halts and halts[0].lon else round(lon1 + (lon2 - lon1) * 0.50, 4),
        ))

        # Stay 2: Pre-Hazard Weather Staging Refuge
        stays.append(StayRecommendation(
            stay_id="stay_pre_hazard",
            name=f"Hilton Garden Inn / Best Western ({dest_city} Approach)",
            location=f"Pre-Hazard Gateway Junction (Approach to {dest_city})",
            highway_exit="Highway Exit 188",
            tier="emergency_shelter",
            price_tier="$$",
            strategic_role="Critical weather refuge positioned immediately before mountain elevation gain or severe wind corridor.",
            amenities=["Emergency Power Generator", "Fleet Heated Parking", "On-site Restaurant", "Snow Chains Available Nearby"],
            contingency_trigger="Deploy immediate booking if DOT issues Chain Control R2/R3, road blizzard advisory, or high-profile wind overturn closures.",
            lat=round(lat1 + (lat2 - lat1) * 0.80 + 0.04, 4),
            lon=round(lon1 + (lon2 - lon1) * 0.80 - 0.04, 4),
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
            lat=round(lat1 + (lat2 - lat1) * 0.65 - 0.03, 4),
            lon=round(lon1 + (lon2 - lon1) * 0.65 + 0.03, 4),
        ))

        return {
            "halts": halts,
            "stays": stays,
        }
