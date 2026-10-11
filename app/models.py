"""
Pydantic data models for the Corporate Travel Disruption Assessment Platform.
Supports Airway, Roadway, and Multimodal corridors with strategic halts and stay recommendations.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TravelMode(str, Enum):
    AIR = "air"
    ROAD = "road"
    MULTIMODAL = "multimodal"


class HighwayPreference(str, Enum):
    INTERSTATE = "interstate"
    STATE_HIGHWAY = "state_highway"
    WEATHER_OPTIMIZED = "weather_optimized"


class RoadwayDisruption(BaseModel):
    highway: str = Field(..., description="e.g. I-80 W, I-95 S, I-70 W")
    segment: str = Field(..., description="Corridor segment, pass, or metro beltway")
    condition_type: str = Field(..., description="chain_control, black_ice, blizzard, flood, construction, normal")
    severity: str = Field(..., description="info, low, medium, high, critical")
    delay_estimate_minutes: int = 0
    description: str
    source: str = "DOT / State 511 Roadway Weather Service"


class HaltSuggestion(BaseModel):
    stop_number: int
    stop_type: str = Field(..., description="rest_stop, fuel_ev_hub, safe_haven_weather_shelter, meal_stop")
    location_name: str
    highway: str
    mile_marker: Optional[str] = None
    distance_from_origin_miles: float
    estimated_drive_time: str
    rationale: str
    facilities: List[str] = Field(default_factory=list)
    lat: Optional[float] = None
    lon: Optional[float] = None


class StayRecommendation(BaseModel):
    stay_id: str
    name: str
    location: str
    highway_exit: str
    tier: str = Field(..., description="business_hotel, budget_motel, emergency_shelter, extended_stay")
    price_tier: str = Field(default="$$", description="$, $$, $$$")
    strategic_role: str = Field(..., description="Why this stay is chosen (e.g. before mountain pass, weather refuge)")
    amenities: List[str] = Field(default_factory=list)
    contingency_trigger: str = Field(..., description="When traveler/ops should execute this stay")
    lat: Optional[float] = None
    lon: Optional[float] = None


class AssessmentRequest(BaseModel):
    origin: str = Field(..., description="Origin airport code (e.g. JFK) or city name (e.g. New York)")
    destination: str = Field(..., description="Destination airport code (e.g. SFO) or city name (e.g. San Francisco)")
    date: str = Field(default="tomorrow", description="'today', 'tomorrow', or YYYY-MM-DD")
    time_window: str = Field(default="all_day", description="'morning', 'afternoon', 'evening', or 'all_day'")
    travel_mode: TravelMode = Field(default=TravelMode.AIR, description="'air', 'road', or 'multimodal'")
    highway_preference: Optional[str] = Field(default="interstate", description="'interstate', 'state_highway', or 'weather_optimized'")
    gemini_api_key: Optional[str] = Field(default=None, description="Optional Google Gemini API key")


class EvidenceItem(BaseModel):
    source: str = Field(..., description="Source name: FAA, NWS, AviationMETAR, TAF, Open-Meteo, DOT Roadway")
    category: str = Field(..., description="airspace, departure_weather, arrival_weather, enroute, roadway")
    title: str
    severity: str = Field(..., description="info, low, medium, high, critical")
    detail: str
    raw_data: Optional[str] = None
    timestamp: Optional[str] = None


class ActionRecommendation(BaseModel):
    target: str = Field(..., description="'traveler' or 'ops_team'")
    category: str = Field(..., description="'timing', 'baggage', 'monitoring', 'routing', 'policy', 'stay'")
    priority: str = Field(..., description="'high', 'medium', 'low'")
    title: str
    action: str
    rationale: str


class UncertaintyAnalysis(BaseModel):
    confidence_score: int = Field(..., ge=0, le=100, description="Overall confidence score 0-100%")
    confidence_tier: str = Field(..., description="'High Confidence', 'Moderate Confidence', 'Higher Uncertainty'")
    confirmed_factors: List[str] = Field(default_factory=list, description="Ground truth / measured realtime data")
    forecast_variables: List[str] = Field(default_factory=list, description="Forward-looking model projections")
    sensitivity_drivers: List[str] = Field(default_factory=list, description="Triggers that could alter risk profile")


class RouteAirportInfo(BaseModel):
    iata: str
    icao: str
    name: str
    city: str
    state: str
    lat: float
    lon: float
    tz: str
    metro: str


class RouteSummary(BaseModel):
    origin: RouteAirportInfo
    destination: RouteAirportInfo
    distance_miles: float
    flight_time_est: str
    flight_time_minutes: int
    midpoint: Dict[str, Any]
    travel_date: str
    time_window: str
    travel_mode: TravelMode = TravelMode.AIR
    driving_distance_miles: Optional[float] = None
    driving_time_est: Optional[str] = None
    primary_interstates: List[str] = Field(default_factory=list)
    highway_preference: Optional[str] = "interstate"
    highway_waypoints: List[Dict[str, Any]] = Field(default_factory=list)


class HourlyForecastItem(BaseModel):
    time: str
    hour_label: str
    temp_c: float
    temp_f: float
    precip_prob: int
    weather_desc: str
    wind_gusts_mph: float
    risk_level: str


class AssessmentResponse(BaseModel):
    route: RouteSummary
    travel_mode: TravelMode = TravelMode.AIR
    composite_risk_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    executive_verdict: str
    headline_risk_summary: str
    
    # Probabilistic estimates
    delay_probability: int = Field(..., ge=0, le=100)
    expected_delay_range: str
    cancellation_probability: int = Field(..., ge=0, le=100)
    missed_connection_risk: int = Field(..., ge=0, le=100)
    
    # Sub-indices
    dimension_scores: Dict[str, int]
    
    # Traceable evidence & actions
    evidence: List[EvidenceItem]
    recommendations: List[ActionRecommendation]
    uncertainty: UncertaintyAnalysis
    
    # Hourly trajectory across travel day
    hourly_timeline: List[HourlyForecastItem]
    
    # Roadway & Stay Extensibility
    roadway_disruptions: List[RoadwayDisruption] = Field(default_factory=list)
    halt_suggestions: List[HaltSuggestion] = Field(default_factory=list)
    stay_recommendations: List[StayRecommendation] = Field(default_factory=list)
    
    # AI synthesis briefing
    ai_briefing: str
    engine_used: str
    generated_at: str
