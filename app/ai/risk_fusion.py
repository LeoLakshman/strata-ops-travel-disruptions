"""
Multi-Signal Probabilistic Risk Fusion Engine.
Synthesizes real-time FAA airspace status, NOAA aviation METAR/TAF, NWS weather alerts,
and high-resolution numerical weather forecasts into a calibrated disruption assessment.
"""

from typing import Dict, List, Tuple, Optional
from datetime import date
from app.models import RiskLevel


class RiskFusionEngine:
    @staticmethod
    def compute_assessment(
        origin_airport: Dict,
        destination_airport: Dict,
        faa_origin: Dict,
        faa_dest: Dict,
        metar_origin: Optional[Dict],
        metar_dest: Optional[Dict],
        nws_origin_alerts: List[Dict],
        nws_dest_alerts: List[Dict],
        forecast_origin: Dict,
        forecast_dest: Dict,
        forecast_midpoint: Dict,
        airsigmets: List[Dict],
        travel_date_str: str = "tomorrow",
        time_window: str = "all_day",
    ) -> Dict:
        """
        Executes multi-source signal fusion and Bayesian risk calculations.
        """
        # 1. Dimension 1: Airspace & ATC Programs (FAA)
        # Weights: Ground stop (95), Ground delay (80), Delays (50)
        faa_score_origin = faa_origin.get("score", 0)
        faa_score_dest = faa_dest.get("score", 0)
        # Destination delays typically hit incoming flights harder than origin departure delays
        airspace_score = int(round(max(faa_score_dest, faa_score_origin * 0.85)))
        
        # 2. Dimension 2: Departure Terminal Conditions
        dep_metar_score = metar_origin.get("risk_score", 10) if metar_origin else 15
        dep_nws_score = max([a.get("score", 0) for a in nws_origin_alerts], default=0)
        dep_fc_score = forecast_origin.get("highest_disruption_score", 10)
        
        is_today = (travel_date_str == "today") or (travel_date_str == date.today().strftime("%Y-%m-%d"))

        # Date weighting: if today, real-time METAR has highest weight; if tomorrow/future, forecast has higher weight
        if is_today:
            dep_weather_score = int(round(dep_metar_score * 0.50 + dep_nws_score * 0.30 + dep_fc_score * 0.20))
        else:
            dep_weather_score = int(round(dep_fc_score * 0.55 + dep_nws_score * 0.30 + dep_metar_score * 0.15))
        dep_weather_score = max(dep_weather_score, dep_nws_score)

        # 3. Dimension 3: Arrival Terminal Conditions
        arr_metar_score = metar_dest.get("risk_score", 10) if metar_dest else 15
        arr_nws_score = max([a.get("score", 0) for a in nws_dest_alerts], default=0)
        arr_fc_score = forecast_dest.get("highest_disruption_score", 10)

        if is_today:
            arr_weather_score = int(round(arr_metar_score * 0.50 + arr_nws_score * 0.30 + arr_fc_score * 0.20))
        else:
            arr_weather_score = int(round(arr_fc_score * 0.55 + arr_nws_score * 0.30 + arr_metar_score * 0.15))
        arr_weather_score = max(arr_weather_score, arr_nws_score)

        # 4. Dimension 4: En-Route & Corridor Airspace
        mid_fc_score = forecast_midpoint.get("highest_disruption_score", 10)
        sigmet_score = min(len(airsigmets) * 12, 75)
        enroute_score = int(round(mid_fc_score * 0.50 + sigmet_score * 0.50))

        # Base composite score calculation (weighted blend)
        weighted_base = (
            airspace_score * 0.35 +
            arr_weather_score * 0.30 +
            dep_weather_score * 0.25 +
            enroute_score * 0.10
        )
        
        # Non-linear catastrophic threat booster:
        # If any single dimension has an extreme hazard (e.g. Ground stop or Blizzard warning),
        # the overall composite risk must reflect this bottleneck.
        peak_threat = max(airspace_score, arr_weather_score, dep_weather_score)
        if peak_threat >= 80:
            composite_score = int(round(max(weighted_base, peak_threat * 0.90)))
        elif peak_threat >= 60:
            composite_score = int(round(max(weighted_base, peak_threat * 0.80)))
        else:
            composite_score = int(round(weighted_base))

        composite_score = max(5, min(98, composite_score))

        # Determine Risk Level Category
        if composite_score >= 80:
            risk_level = RiskLevel.CRITICAL
        elif composite_score >= 60:
            risk_level = RiskLevel.HIGH
        elif composite_score >= 35:
            risk_level = RiskLevel.MODERATE
        else:
            risk_level = RiskLevel.LOW

        # Probabilistic Disruption Metrics
        # Delay Probability: calibrated against composite score
        delay_prob = int(round(min(95, max(10, composite_score * 0.92 + 5))))
        
        # Expected delay duration estimate
        if composite_score >= 80:
            expected_delay = "90 to 180+ minutes (Severe)"
        elif composite_score >= 60:
            expected_delay = "45 to 90 minutes (Significant)"
        elif composite_score >= 35:
            expected_delay = "20 to 45 minutes (Moderate)"
        else:
            expected_delay = "0 to 15 minutes (Normal)"

        # Cancellation Probability
        # Cancellations usually require severe weather, blizzard, or multi-hour ground stops
        if composite_score >= 85:
            cancellation_prob = min(85, int(round(composite_score * 0.70)))
        elif composite_score >= 70:
            cancellation_prob = int(round(composite_score * 0.35))
        elif composite_score >= 50:
            cancellation_prob = 15
        else:
            cancellation_prob = 4

        # Missed Connection Risk (Vulnerability for multi-leg itineraries)
        # Even a 30-min delay can break a 45-min hub connection
        missed_connection_risk = int(round(min(95, max(8, delay_prob * 1.15 if composite_score > 30 else 12))))

        # Executive Verdict Formulation
        verdict = RiskFusionEngine._craft_executive_verdict(
            risk_level,
            composite_score,
            faa_dest,
            faa_origin,
            metar_dest,
            forecast_dest,
            nws_dest_alerts,
            nws_origin_alerts
        )

        return {
            "composite_score": composite_score,
            "risk_level": risk_level,
            "executive_verdict": verdict["verdict"],
            "headline_summary": verdict["headline"],
            "delay_probability": delay_prob,
            "expected_delay_range": expected_delay,
            "cancellation_probability": cancellation_prob,
            "missed_connection_risk": missed_connection_risk,
            "dimension_scores": {
                "airspace_atc": airspace_score,
                "departure_terminal": dep_weather_score,
                "arrival_terminal": arr_weather_score,
                "enroute_corridor": enroute_score,
            }
        }

    @staticmethod
    def _craft_executive_verdict(
        risk_level: RiskLevel,
        score: int,
        faa_dest: Dict,
        faa_origin: Dict,
        metar_dest: Optional[Dict],
        forecast_dest: Dict,
        nws_dest_alerts: List[Dict],
        nws_origin_alerts: List[Dict],
    ) -> Dict[str, str]:
        """
        Synthesizes an immediate operational headline and executive verdict.
        """
        # Check active FAA programs
        if faa_dest.get("ground_stops"):
            arpt = faa_dest["airport"]
            reason = faa_dest["ground_stops"][0].get("reason", "operations")
            return {
                "verdict": f"CRITICAL RISK: Active FAA Ground Stop at destination ({arpt}) due to {reason}.",
                "headline": f"FAA has halted incoming flights to {arpt}. Significant flight holds and cancellations expected.",
            }
        if faa_dest.get("ground_delays"):
            arpt = faa_dest["airport"]
            gd = faa_dest["ground_delays"][0]
            avg = gd.get("avg_delay", "over 45m")
            reason = gd.get("reason", "weather")
            return {
                "verdict": f"HIGH RISK: FAA Ground Delay Program active at {arpt} (Avg {avg} delay).",
                "headline": f"Destination airport is operating under constrained arrival slots due to {reason}.",
            }
            
        # Check severe NWS alerts
        all_alerts = nws_dest_alerts + nws_origin_alerts
        severe_alerts = [a for a in all_alerts if a.get("score", 0) >= 70]
        if severe_alerts:
            top_ev = severe_alerts[0].get("event", "Severe Weather")
            loc = severe_alerts[0].get("location", "Terminal area")
            return {
                "verdict": f"HIGH RISK: {top_ev} active in {loc}.",
                "headline": f"Official National Weather Service advisory indicates imminent disruption to flight operations.",
            }

        # Check IFR / LIFR conditions
        if metar_dest and metar_dest.get("flight_category") in ("IFR", "LIFR"):
            cat = metar_dest["flight_category"]
            vis = metar_dest.get("visibility_sm", 3)
            return {
                "verdict": f"MODERATE TO HIGH RISK: {cat} instrument conditions at destination (Visibility {vis}SM).",
                "headline": "Low cloud ceilings and reduced visibility are reducing runway acceptance rates.",
            }

        # Forecast conditions
        if forecast_dest.get("max_wind_gust_mph", 0) >= 35:
            gust = forecast_dest["max_wind_gust_mph"]
            return {
                "verdict": f"MODERATE RISK: Strong wind gusts forecasted (up to {gust} mph).",
                "headline": "Crosswinds may force single-runway operations, causing cascading arrival delays.",
            }

        if risk_level == RiskLevel.LOW:
            return {
                "verdict": "LOW RISK: Favorable airspace and atmospheric conditions along route.",
                "headline": "No active FAA ground programs or hazardous weather systems detected for this flight window.",
            }
        elif risk_level == RiskLevel.MODERATE:
            return {
                "verdict": "MODERATE RISK: Minor meteorological or traffic friction along corridor.",
                "headline": "Standard schedule buffers recommended. Minor delays of 15-30 minutes possible.",
            }
        elif risk_level == RiskLevel.HIGH:
            return {
                "verdict": "HIGH RISK: Meaningful operational bottlenecks identified.",
                "headline": "Multiple environmental and capacity signals indicate elevated risk of flight delay or missed connections.",
            }
        else:
            return {
                "verdict": "CRITICAL RISK: Severe disruptions expected.",
                "headline": "Major ground constraints, systemic airspace delays, or hazardous weather actively impacting itinerary.",
            }
