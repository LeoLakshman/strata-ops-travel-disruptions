"""
FastAPI Application for Corporate Travel Disruption Assessment Platform.
Integrates live FAA NAS status, NOAA NWS alerts, AviationWeather METAR/TAF,
and Open-Meteo numerical atmospheric models with AI signal fusion and LLM synthesis.
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

from app.models import (
    AssessmentRequest,
    AssessmentResponse,
    RouteSummary,
    RouteAirportInfo,
    HourlyForecastItem,
    RiskLevel,
    AlternateRouteSuggestion,
    JourneyChatRequest,
    JourneyChatResponse,
)
from app.airports import (
    resolve_airport,
    search_airports,
    calculate_flight_route,
    AIRPORTS_DB,
)
from app.services.faa_service import FAAService
from app.services.aviation_weather_service import AviationWeatherService
from app.services.nws_service import NWSService
from app.services.forecast_service import ForecastService
from app.services.roadway_service import RoadwayService
from app.services.stay_service import StayService
from app.services.rerouting_service import ReroutingService
from app.ai.risk_fusion import RiskFusionEngine
from app.ai.synthesizer import DisruptionSynthesizer
from app.ai.llm_client import GeminiAIClient
from app.ai.chat_assistant import JourneyChatAssistant

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("app.main")

app = FastAPI(
    title="Strata Ops // U.S. Corporate Travel Disruption Intelligence",
    description="Multi-source real-time flight disruption risk assessment and decision support platform.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/airports")
async def get_airports(q: Optional[str] = Query(None, description="Search query for airport code or city")):
    """
    Search and auto-complete US airports.
    """
    results = search_airports(q or "", limit=10)
    return {"airports": results}


@app.get("/api/nas-status")
async def get_nas_status():
    """
    Returns live FAA National Airspace System programs (Ground Stops, GDPs, Delays, Closures).
    """
    nas = await FAAService.fetch_nas_status()
    return nas


@app.get("/api/health")
async def health_check():
    """
    Verifies service health and external API connectivity status.
    """
    has_gemini = GeminiAIClient.is_available()
    return {
        "status": "online",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "gemini_configured": has_gemini,
        "external_sources": {
            "faa_nas": "https://nasstatus.faa.gov",
            "noaa_nws": "https://api.weather.gov",
            "aviation_weather": "https://aviationweather.gov",
            "open_meteo": "https://api.open-meteo.com",
        }
    }


@app.get("/api/config")
async def get_app_config():
    """
    Exposes client configuration including optional TomTom and Gemini capabilities.
    """
    tomtom_key = os.environ.get("TOMTOM_API_KEY", "")
    return {
        "gemini_configured": GeminiAIClient.is_available(),
        "tomtom_configured": bool(tomtom_key),
        "tomtom_key": tomtom_key or None,
    }


@app.post("/api/assess", response_model=AssessmentResponse)
async def assess_travel_disruption(req: AssessmentRequest):
    """
    Core Disruption Assessment Endpoint.
    Gathers and fuses live data from 4 external sources to produce an operational risk assessment.
    """
    # 1. Resolve Origin and Destination
    orig_airport = resolve_airport(req.origin)
    if not orig_airport:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to resolve origin location '{req.origin}'. Please enter a valid US airport code (e.g. JFK, ORD) or city name."
        )

    dest_airport = resolve_airport(req.destination)
    if not dest_airport:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to resolve destination location '{req.destination}'. Please enter a valid US airport code (e.g. SFO, LAX) or city name."
        )

    if orig_airport["iata"] == dest_airport["iata"]:
        raise HTTPException(
            status_code=400,
            detail="Origin and destination airports cannot be the same."
        )

    # 2. Calculate Great-Circle Flight Route & Midpoint
    route_calc = calculate_flight_route(orig_airport, dest_airport)
    midpoint = route_calc["midpoint"]

    logger.info(
        f"Processing disruption assessment: {orig_airport['iata']} -> {dest_airport['iata']} "
        f"({route_calc['distance_miles']} mi) for date={req.date}"
    )

    # 3. Parallel Telemetry Retrieval from 4 External Data Sources
    # Fetch: FAA NAS, AviationWeather METAR/TAF/SIGMETs, NWS Alerts, Open-Meteo Forecasts
    orig_icao = orig_airport["icao"]
    dest_icao = dest_airport["icao"]

    faa_task = FAAService.fetch_nas_status()
    metar_task = AviationWeatherService.get_metar([orig_icao, dest_icao])
    taf_task = AviationWeatherService.get_taf([orig_icao, dest_icao])
    sigmet_task = AviationWeatherService.get_active_airsigmets()
    nws_orig_task = NWSService.get_alerts_for_point(orig_airport["lat"], orig_airport["lon"], orig_airport["city"])
    nws_dest_task = NWSService.get_alerts_for_point(dest_airport["lat"], dest_airport["lon"], dest_airport["city"])
    fc_orig_task = ForecastService.get_hourly_forecast(orig_airport["lat"], orig_airport["lon"], req.date, orig_airport["tz"])
    fc_dest_task = ForecastService.get_hourly_forecast(dest_airport["lat"], dest_airport["lon"], req.date, dest_airport["tz"])
    fc_mid_task = ForecastService.get_hourly_forecast(midpoint["lat"], midpoint["lon"], req.date, "auto")

    (
        nas_status,
        metar_map,
        taf_map,
        airsigmets,
        nws_origin_alerts,
        nws_dest_alerts,
        forecast_origin,
        forecast_dest,
        forecast_midpoint,
    ) = await asyncio.gather(
        faa_task,
        metar_task,
        taf_task,
        sigmet_task,
        nws_orig_task,
        nws_dest_task,
        fc_orig_task,
        fc_dest_task,
        fc_mid_task,
        return_exceptions=False,
    )

    # Filter FAA programs specifically for origin and destination
    faa_origin = FAAService.get_airport_faa_status(nas_status, orig_airport["iata"])
    faa_dest = FAAService.get_airport_faa_status(nas_status, dest_airport["iata"])

    metar_origin = metar_map.get(orig_icao)
    metar_dest = metar_map.get(dest_icao)
    taf_origin = taf_map.get(orig_icao)
    taf_dest = taf_map.get(dest_icao)

    # 4. Multi-Signal Bayesian Risk Fusion Calculation
    fusion_result = RiskFusionEngine.compute_assessment(
        origin_airport=orig_airport,
        destination_airport=dest_airport,
        faa_origin=faa_origin,
        faa_dest=faa_dest,
        metar_origin=metar_origin,
        metar_dest=metar_dest,
        nws_origin_alerts=nws_origin_alerts,
        nws_dest_alerts=nws_dest_alerts,
        forecast_origin=forecast_origin,
        forecast_dest=forecast_dest,
        forecast_midpoint=forecast_midpoint,
        airsigmets=airsigmets,
        travel_date_str=req.date,
        time_window=req.time_window,
        travel_mode=req.travel_mode.value,
    )

    # 5. Roadway Corridor & Strategic Stay Computations (Extensible Multimodal Engine)
    road_route = RoadwayService.calculate_road_route(
        origin=orig_airport,
        destination=dest_airport,
        flight_distance_miles=route_calc["distance_miles"],
        highway_preference=req.highway_preference or "interstate",
    )
    roadway_disruptions = RoadwayService.assess_roadway_hazards(
        origin=orig_airport,
        destination=dest_airport,
        weather_origin=forecast_origin,
        weather_dest=forecast_dest,
        weather_midpoint=forecast_midpoint,
    )
    halts_and_stays = StayService.generate_halts_and_stays(
        origin=orig_airport,
        destination=dest_airport,
        driving_distance_miles=road_route["driving_distance_miles"],
        roadway_hazards=roadway_disruptions,
        composite_risk_score=fusion_result["composite_score"],
    )
    alternate_routes = ReroutingService.generate_alternate_routes(
        origin=orig_airport,
        destination=dest_airport,
        travel_mode=req.travel_mode.value,
        composite_risk_score=fusion_result["composite_score"],
        driving_distance_miles=road_route["driving_distance_miles"],
        flight_distance_miles=route_calc["distance_miles"],
        faa_dest=faa_dest,
        forecast_dest=forecast_dest,
        roadway_hazards=roadway_disruptions,
    )

    # 6. Synthesize Traceable Evidence Dossier
    evidence_items = DisruptionSynthesizer.build_evidence_dossier(
        origin_airport=orig_airport,
        destination_airport=dest_airport,
        faa_origin=faa_origin,
        faa_dest=faa_dest,
        metar_origin=metar_origin,
        metar_dest=metar_dest,
        taf_origin=taf_origin,
        taf_dest=taf_dest,
        nws_origin_alerts=nws_origin_alerts,
        nws_dest_alerts=nws_dest_alerts,
        forecast_origin=forecast_origin,
        forecast_dest=forecast_dest,
        forecast_midpoint=forecast_midpoint,
        airsigmets=airsigmets,
        roadway_disruptions=roadway_disruptions,
    )

    # Hourly Timeline parsing
    dest_hourly = forecast_dest.get("hourly_timeline", [])
    timeline_items: List[HourlyForecastItem] = []
    for h in dest_hourly:
        timeline_items.append(HourlyForecastItem(
            time=h["time"],
            hour_label=h["hour_label"],
            temp_c=h["temp_c"],
            temp_f=h["temp_f"],
            precip_prob=h["precip_prob"],
            weather_desc=h["weather_desc"],
            wind_gusts_mph=h["wind_gusts_mph"],
            risk_level=h["severity"],
        ))

    # 7. Actionable Guidance Matrix (Includes Roadway & Lodging recommendations)
    recommendations = DisruptionSynthesizer.build_recommendations(
        risk_level=fusion_result["risk_level"],
        composite_score=fusion_result["composite_score"],
        origin_airport=orig_airport,
        destination_airport=dest_airport,
        faa_dest=faa_dest,
        metar_dest=metar_dest,
        forecast_dest=forecast_dest,
        hourly_timeline=dest_hourly,
        roadway_disruptions=roadway_disruptions,
        travel_mode=req.travel_mode.value,
    )

    # 8. Uncertainty Analysis & Confidence Quantification
    uncertainty = DisruptionSynthesizer.analyze_uncertainty(
        composite_score=fusion_result["composite_score"],
        travel_date_str=req.date,
        faa_dest=faa_dest,
        metar_dest=metar_dest,
        forecast_dest=forecast_dest,
        nws_dest_alerts=nws_dest_alerts,
        travel_mode=req.travel_mode.value,
    )

    # 8. AI Synthesis & Executive Briefing
    route_summary_dict = {
        "origin": orig_airport,
        "destination": dest_airport,
        "distance_miles": route_calc["distance_miles"],
        "flight_time_est": route_calc["flight_time_est"],
        "travel_date": req.date,
    }

    # Attempt LLM synthesis if Gemini API key is provided
    gemini_key = req.gemini_api_key or os.getenv("GEMINI_API_KEY")
    ai_briefing = None
    engine_used = "AeroGuard Operational Bayesian Engine"

    if gemini_key:
        evidence_dicts = [e.dict() for e in evidence_items]
        ai_briefing = await GeminiAIClient.generate_synthesis(
            route_summary=route_summary_dict,
            composite_score=fusion_result["composite_score"],
            risk_level=fusion_result["risk_level"].value,
            delay_prob=fusion_result["delay_probability"],
            expected_delay=fusion_result["expected_delay_range"],
            evidence=evidence_dicts,
            uncertainty=uncertainty.dict(),
            custom_key=gemini_key,
        )
        if ai_briefing:
            engine_used = "Google Gemini 2.5 Flash"

    # Fallback to built-in deterministic synthesizer
    if not ai_briefing:
        ai_briefing = DisruptionSynthesizer.generate_briefing(
            route_summary=route_summary_dict,
            risk_level=fusion_result["risk_level"],
            composite_score=fusion_result["composite_score"],
            verdict=fusion_result["executive_verdict"],
            delay_prob=fusion_result["delay_probability"],
            expected_delay=fusion_result["expected_delay_range"],
            evidence=evidence_items,
            uncertainty=uncertainty,
        )

    # Assemble complete response
    route_obj = RouteSummary(
        origin=RouteAirportInfo(**orig_airport),
        destination=RouteAirportInfo(**dest_airport),
        distance_miles=route_calc["distance_miles"],
        flight_time_est=route_calc["flight_time_est"],
        flight_time_minutes=route_calc["flight_time_minutes"],
        midpoint=midpoint,
        travel_date=req.date,
        time_window=req.time_window,
        travel_mode=req.travel_mode,
        driving_distance_miles=road_route["driving_distance_miles"],
        driving_time_est=road_route["driving_time_est"],
        primary_interstates=road_route["primary_interstates"],
        highway_preference=road_route.get("highway_preference", "interstate"),
        highway_waypoints=road_route.get("highway_waypoints", []),
    )

    return AssessmentResponse(
        route=route_obj,
        travel_mode=req.travel_mode,
        composite_risk_score=fusion_result["composite_score"],
        risk_level=fusion_result["risk_level"],
        executive_verdict=fusion_result["executive_verdict"],
        headline_risk_summary=fusion_result["headline_summary"],
        delay_probability=fusion_result["delay_probability"],
        expected_delay_range=fusion_result["expected_delay_range"],
        cancellation_probability=fusion_result["cancellation_probability"],
        missed_connection_risk=fusion_result["missed_connection_risk"],
        dimension_scores=fusion_result["dimension_scores"],
        evidence=evidence_items,
        recommendations=recommendations,
        uncertainty=uncertainty,
        hourly_timeline=timeline_items,
        roadway_disruptions=roadway_disruptions,
        halt_suggestions=halts_and_stays["halts"],
        stay_recommendations=halts_and_stays["stays"],
        alternate_routes=alternate_routes,
        ai_briefing=ai_briefing,
        engine_used=engine_used,
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    )


@app.post("/api/chat-assistant", response_model=JourneyChatResponse)
async def chat_journey_assistant(req: JourneyChatRequest):
    """
    Real-Time Conversational Journey Disruption Assistant.
    Provides interactive answers, delay mitigations, draft stakeholder notices,
    and rerouting recommendations grounded in the live assessment context.
    """
    return await JourneyChatAssistant.process_chat(req)


# Serve Static Assets for the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.api_route("/", methods=["GET", "HEAD"])
async def serve_index():
    """
    Serves the primary web dashboard UI with no-cache headers.
    """
    return FileResponse("static/index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
