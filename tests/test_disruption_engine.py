"""
Unit & Integration Test Suite for Strata Ops Travel Disruption Intelligence Platform.
"""

import pytest
from app.airports import resolve_airport, calculate_flight_route, search_airports
from app.services.faa_service import FAAService
from app.services.aviation_weather_service import AviationWeatherService
from app.services.nws_service import NWSService
from app.ai.risk_fusion import RiskFusionEngine
from app.ai.synthesizer import DisruptionSynthesizer
from app.models import RiskLevel


def test_airport_resolution():
    # Direct IATA
    jfk = resolve_airport("JFK")
    assert jfk is not None
    assert jfk["iata"] == "JFK"
    assert jfk["icao"] == "KJFK"
    assert jfk["city"] == "New York"

    # ICAO format
    sfo = resolve_airport("KSFO")
    assert sfo is not None
    assert sfo["iata"] == "SFO"

    # City alias
    chicago = resolve_airport("Chicago")
    assert chicago is not None
    assert chicago["iata"] in ("ORD", "MDW")

    ny = resolve_airport("New York")
    assert ny is not None
    assert ny["iata"] == "JFK"

    sf = resolve_airport("San Francisco")
    assert sf is not None
    assert sf["iata"] == "SFO"

    # Lubbock (LBB) comprehensive resolution
    lbb = resolve_airport("LBB")
    assert lbb is not None
    assert lbb["iata"] == "LBB"
    assert lbb["icao"] == "KLBB"
    assert "Lubbock" in lbb["city"]

    assert resolve_airport("KLBB")["iata"] == "LBB"
    assert resolve_airport("Lubbock")["iata"] == "LBB"
    assert resolve_airport("Lubbock, TX")["iata"] == "LBB"
    assert resolve_airport("Lubbock airport")["iata"] == "LBB"

    # Other regional airports
    assert resolve_airport("AMA")["iata"] == "AMA"
    assert resolve_airport("Amarillo")["iata"] == "AMA"
    assert resolve_airport("TYS")["iata"] == "TYS"

    # Non-existent
    assert resolve_airport("XYZ999") is None


def test_route_calculation():
    jfk = resolve_airport("JFK")
    sfo = resolve_airport("SFO")
    route = calculate_flight_route(jfk, sfo)

    assert 2400 < route["distance_miles"] < 2700
    assert route["flight_time_minutes"] > 300
    assert "midpoint" in route
    assert 35 < route["midpoint"]["lat"] < 45
    assert -105 < route["midpoint"]["lon"] < -90


def test_airport_search():
    res = search_airports("bos", limit=5)
    assert len(res) > 0
    assert any(a["iata"] == "BOS" for a in res)


def test_faa_xml_parser():
    sample_xml = """<AIRPORT_STATUS_INFORMATION>
    <Update_Time>Sun Oct 11 17:36:34 2026 GMT</Update_Time>
    <Delay_type>
        <Name>Ground Stop Programs</Name>
        <Ground_Stop_List>
            <Program>
                <ARPT>RDU</ARPT>
                <Reason>thunderstorms</Reason>
                <End_Time>1:45 pm EDT</End_Time>
            </Program>
        </Ground_Stop_List>
    </Delay_type>
    <Delay_type>
        <Name>Ground Delay Programs</Name>
        <Ground_Delay_List>
            <Ground_Delay>
                <ARPT>LAS</ARPT>
                <Reason>low ceilings</Reason>
                <Avg>51 minutes</Avg>
                <Max>3 hours and 9 minutes</Max>
            </Ground_Delay>
        </Ground_Delay_List>
    </Delay_type>
    </AIRPORT_STATUS_INFORMATION>"""

    parsed = FAAService._parse_faa_xml(sample_xml)
    assert parsed["available"] is True
    assert len(parsed["ground_stops"]) == 1
    assert parsed["ground_stops"][0]["airport"] == "RDU"
    assert parsed["ground_stops"][0]["reason"] == "thunderstorms"
    assert parsed["ground_stops"][0]["severity"] == "critical"

    assert len(parsed["ground_delays"]) == 1
    assert parsed["ground_delays"][0]["airport"] == "LAS"
    assert parsed["ground_delays"][0]["avg_delay"] == "51 minutes"

    # Check airport lookup
    las_status = FAAService.get_airport_faa_status(parsed, "LAS")
    assert las_status["has_disruption"] is True
    assert las_status["score"] == 80


def test_metar_processing():
    sample_metar_json = {
        "icaoId": "KJFK",
        "temp": 12,
        "dewp": 11,
        "wspd": 18,
        "wgst": 28,
        "visib": 2.5,
        "fltCat": "IFR",
        "cover": [{"cover": "OVC", "base": 800}],
        "rawOb": "METAR KJFK 111800Z 08018G28KT 2 1/2SM OVC008 12/11",
        "reportTime": "2026-10-11T18:00:00.000Z",
    }
    processed = AviationWeatherService._process_metar_item(sample_metar_json)
    assert processed["flight_category"] == "IFR"
    assert processed["risk_severity"] == "high"
    assert processed["visibility_sm"] == 2.5
    assert processed["ceiling_ft"] == 800
    assert processed["wind_gust_kts"] == 28


def test_nws_alert_scoring():
    score_blizzard = NWSService._calculate_alert_score("Blizzard Warning", "severe", "immediate")
    assert score_blizzard >= 80

    score_wind = NWSService._calculate_alert_score("Wind Advisory", "minor", "expected")
    assert score_wind <= 40


def test_risk_fusion_engine():
    orig = resolve_airport("JFK")
    dest = resolve_airport("SFO")

    # Test benign conditions -> Low risk
    benign_faa = {"has_disruption": False, "score": 0, "ground_stops": [], "ground_delays": []}
    benign_metar = {"risk_score": 10, "flight_category": "VFR"}
    benign_fc = {"highest_disruption_score": 10, "max_wind_gust_mph": 10}

    low_res = RiskFusionEngine.compute_assessment(
        origin_airport=orig,
        destination_airport=dest,
        faa_origin=benign_faa,
        faa_dest=benign_faa,
        metar_origin=benign_metar,
        metar_dest=benign_metar,
        nws_origin_alerts=[],
        nws_dest_alerts=[],
        forecast_origin=benign_fc,
        forecast_dest=benign_fc,
        forecast_midpoint=benign_fc,
        airsigmets=[],
        travel_date_str="tomorrow",
    )
    assert low_res["risk_level"] == RiskLevel.LOW
    assert low_res["composite_score"] <= 35
    assert low_res["delay_probability"] <= 35

    # Test severe Ground Stop at destination -> Critical risk
    critical_faa = {
        "airport": "SFO",
        "has_disruption": True,
        "score": 95,
        "ground_stops": [{"airport": "SFO", "reason": "thunderstorms", "end_time": "20:00Z"}]
    }
    crit_res = RiskFusionEngine.compute_assessment(
        origin_airport=orig,
        destination_airport=dest,
        faa_origin=benign_faa,
        faa_dest=critical_faa,
        metar_origin=benign_metar,
        metar_dest=benign_metar,
        nws_origin_alerts=[],
        nws_dest_alerts=[],
        forecast_origin=benign_fc,
        forecast_dest=benign_fc,
        forecast_midpoint=benign_fc,
        airsigmets=[],
        travel_date_str="today",
    )
    assert crit_res["risk_level"] in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    assert crit_res["composite_score"] >= 75
    assert "Ground Stop" in crit_res["executive_verdict"]


def test_uncertainty_quantification():
    dest_faa = {"airport": "SFO", "has_disruption": False, "ground_stops": [], "ground_delays": []}
    dest_metar = {"flight_category": "VFR", "visibility_sm": 10, "ceiling_ft": 5000}
    dest_fc = {"max_precip_prob": 20, "max_wind_gust_mph": 15}

    unc = DisruptionSynthesizer.analyze_uncertainty(
        composite_score=25,
        travel_date_str="tomorrow",
        faa_dest=dest_faa,
        metar_dest=dest_metar,
        forecast_dest=dest_fc,
        nws_dest_alerts=[]
    )
    assert 70 <= unc.confidence_score <= 95
    assert len(unc.confirmed_factors) > 0
    assert len(unc.forecast_variables) > 0
    assert len(unc.sensitivity_drivers) > 0


def test_roadway_service():
    from app.services.roadway_service import RoadwayService
    orig = resolve_airport("DFW")
    dest = resolve_airport("LBB")
    
    # 1. Test Interstate route
    road_route_i = RoadwayService.calculate_road_route(orig, dest, 281.0, "interstate")
    assert road_route_i["driving_distance_miles"] > 281.0
    assert "h" in road_route_i["driving_time_est"]
    assert any("I-20" in h for h in road_route_i["primary_interstates"])
    assert len(road_route_i["highway_waypoints"]) >= 5
    assert all("lat" in wp and "lon" in wp for wp in road_route_i["highway_waypoints"])

    # 2. Test State Highway route
    road_route_sh = RoadwayService.calculate_road_route(orig, dest, 281.0, "state_highway")
    assert any("TX-114" in h or "US-380" in h for h in road_route_sh["primary_interstates"])
    assert len(road_route_sh["highway_waypoints"]) >= 5

    # 3. Test Weather-Optimized route
    road_route_wo = RoadwayService.calculate_road_route(orig, dest, 281.0, "weather_optimized")
    assert any("US-84" in h or "Bypass" in h for h in road_route_wo["primary_interstates"])
    assert len(road_route_wo["highway_waypoints"]) >= 5

    hazards = RoadwayService.assess_roadway_hazards(
        orig,
        dest,
        weather_origin={"max_wind_gust_mph": 20},
        weather_dest={"max_wind_gust_mph": 45, "temp_c": -1.0, "max_precip_prob": 70},
        weather_midpoint={"max_wind_gust_mph": 25},
    )
    assert len(hazards) >= 1
    condition_types = [h.condition_type for h in hazards]
    assert "high_wind_warning" in condition_types or "black_ice" in condition_types or "chain_control" in condition_types


def test_stay_service():
    from app.services.stay_service import StayService
    orig = resolve_airport("DFW")
    dest = resolve_airport("LBB")

    res = StayService.generate_halts_and_stays(orig, dest, 350.0, [], 75)
    halts = res["halts"]
    stays = res["stays"]

    assert len(halts) >= 3
    assert any(h.stop_type == "fuel_ev_hub" for h in halts)
    assert any(h.stop_type == "safe_haven_weather_shelter" for h in halts)
    assert all(h.lat is not None and h.lon is not None for h in halts)

    assert len(stays) >= 3
    assert any(s.tier == "emergency_shelter" for s in stays)
    assert any(s.tier == "business_hotel" for s in stays)
    assert all(s.lat is not None and s.lon is not None for s in stays)
    assert all(len(s.amenities) > 0 for s in stays)
    assert all(len(s.contingency_trigger) > 0 for s in stays)


def test_lubbock_airport_resolution():
    lbb = resolve_airport("LBB")
    assert lbb is not None
    assert lbb["iata"] == "LBB"
    assert lbb["icao"] == "KLBB"
    assert "Lubbock" in lbb["city"]
    assert lbb["state"] == "TX"

    lubbock_city = resolve_airport("Lubbock, TX")
    assert lubbock_city is not None
    assert lubbock_city["iata"] == "LBB"

    preston_smith = resolve_airport("Preston Smith")
    assert preston_smith is not None
    assert preston_smith["iata"] == "LBB"
