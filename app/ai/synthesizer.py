"""
Operational Disruption Synthesizer & Evidence Attribution Engine.
Assembles verifiable evidence dossiers, formulates role-specific action guidance,
and articulates confidence and uncertainty boundaries.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from app.models import (
    EvidenceItem,
    ActionRecommendation,
    UncertaintyAnalysis,
    HourlyForecastItem,
    RiskLevel,
)


class DisruptionSynthesizer:
    @staticmethod
    def build_evidence_dossier(
        origin_airport: Dict,
        destination_airport: Dict,
        faa_origin: Dict,
        faa_dest: Dict,
        metar_origin: Optional[Dict],
        metar_dest: Optional[Dict],
        taf_origin: Optional[Dict],
        taf_dest: Optional[Dict],
        nws_origin_alerts: List[Dict],
        nws_dest_alerts: List[Dict],
        forecast_origin: Dict,
        forecast_dest: Dict,
        forecast_midpoint: Dict,
        airsigmets: List[Dict],
        roadway_disruptions: Optional[List[Any]] = None,
    ) -> List[EvidenceItem]:
        """
        Builds a comprehensive, traceable evidence dossier linking every risk factor
        directly to official FAA, NOAA, NWS, and Open-Meteo observations.
        """
        evidence: List[EvidenceItem] = []
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        # 1. FAA Evidence - Destination
        if faa_dest.get("ground_stops"):
            for gs in faa_dest["ground_stops"]:
                evidence.append(EvidenceItem(
                    source="FAA Command Center (ATCSCC)",
                    category="airspace",
                    title=f"Active Ground Stop at {destination_airport['iata']}",
                    severity="critical",
                    detail=f"FAA has halted flights destined for {destination_airport['iata']}. Reason: {gs.get('reason')}. Expected expiration: {gs.get('end_time') or 'Indefinite'}.",
                    raw_data=f"FAA Program: Ground Stop | Airport: {gs.get('airport')} | Reason: {gs.get('reason')} | End Time: {gs.get('end_time')}",
                    timestamp=now_str,
                ))

        if faa_dest.get("ground_delays"):
            for gd in faa_dest["ground_delays"]:
                evidence.append(EvidenceItem(
                    source="FAA Command Center (ATCSCC)",
                    category="airspace",
                    title=f"Ground Delay Program (GDP) at {destination_airport['iata']}",
                    severity="high",
                    detail=f"Traffic management initiative active. Inbound flights delayed an average of {gd.get('avg_delay')} (maximum {gd.get('max_delay')}). Primary root cause: {gd.get('reason')}.",
                    raw_data=f"FAA GDP: {gd.get('airport')} | Avg: {gd.get('avg_delay')} | Max: {gd.get('max_delay')} | Reason: {gd.get('reason')}",
                    timestamp=now_str,
                ))

        if faa_dest.get("arrival_departure_delays"):
            for ad in faa_dest["arrival_departure_delays"]:
                evidence.append(EvidenceItem(
                    source="FAA Command Center (ATCSCC)",
                    category="airspace",
                    title=f"{ad.get('program_type')} at {destination_airport['iata']}",
                    severity="medium",
                    detail=f"Delays of {ad.get('min_delay')} to {ad.get('max_delay')} reported. Trend: {ad.get('trend')}. Cause: {ad.get('reason')}.",
                    raw_data=f"FAA Delay Info: {ad.get('airport')} | Range: {ad.get('min_delay')}-{ad.get('max_delay')} | Reason: {ad.get('reason')}",
                    timestamp=now_str,
                ))

        # 2. FAA Evidence - Origin
        if faa_origin.get("ground_stops") or faa_origin.get("ground_delays"):
            orig_programs = faa_origin.get("ground_stops", []) + faa_origin.get("ground_delays", [])
            for p in orig_programs:
                evidence.append(EvidenceItem(
                    source="FAA Command Center (ATCSCC)",
                    category="airspace",
                    title=f"Departure Airport ATC Initiative: {origin_airport['iata']}",
                    severity="high",
                    detail=f"Origin airport is currently subject to an FAA program ({p.get('program_type')}) due to {p.get('reason')}.",
                    raw_data=str(p),
                    timestamp=now_str,
                ))

        # 3. NOAA Aviation Weather METAR - Origin
        if metar_origin:
            flt_cat = metar_origin.get("flight_category", "VFR")
            sev = "critical" if flt_cat == "LIFR" else "high" if flt_cat == "IFR" else "medium" if flt_cat == "MVFR" else "info"
            evidence.append(EvidenceItem(
                source="NOAA Aviation Weather Center",
                category="departure_weather",
                title=f"Departure METAR Observation ({origin_airport['iata']}): {flt_cat}",
                severity=sev,
                detail=f"Conditions: {metar_origin.get('category_desc')}. Visibility: {metar_origin.get('visibility_sm')} SM. Wind: {metar_origin.get('wind_speed_kts')} kts (Gusts: {metar_origin.get('wind_gust_kts') or 'None'}). Weather: {metar_origin.get('weather_phenomena')}.",
                raw_data=metar_origin.get("raw_observation"),
                timestamp=str(metar_origin.get("observation_time")) if metar_origin.get("observation_time") else now_str,
            ))

        # 4. NOAA Aviation Weather METAR - Destination
        if metar_dest:
            flt_cat = metar_dest.get("flight_category", "VFR")
            sev = "critical" if flt_cat == "LIFR" else "high" if flt_cat == "IFR" else "medium" if flt_cat == "MVFR" else "info"
            evidence.append(EvidenceItem(
                source="NOAA Aviation Weather Center",
                category="arrival_weather",
                title=f"Arrival METAR Observation ({destination_airport['iata']}): {flt_cat}",
                severity=sev,
                detail=f"Conditions: {metar_dest.get('category_desc')}. Visibility: {metar_dest.get('visibility_sm')} SM. Ceiling: {metar_dest.get('ceiling_ft') or 'Unlimited'} ft. Wind: {metar_dest.get('wind_speed_kts')} kts (Gusts: {metar_dest.get('wind_gust_kts') or 'None'}).",
                raw_data=metar_dest.get("raw_observation"),
                timestamp=str(metar_dest.get("observation_time")) if metar_dest.get("observation_time") else now_str,
            ))

        # 5. Terminal Aerodrome Forecast (TAF)
        if taf_dest and taf_dest.get("raw_taf"):
            evidence.append(EvidenceItem(
                source="NOAA Aviation Weather Center",
                category="arrival_weather",
                title=f"Terminal Aerodrome Forecast (TAF) for {destination_airport['iata']}",
                severity="info",
                detail=f"Official 24-30 hour aviation forecast for {destination_airport['iata']} airspace operations.",
                raw_data=taf_dest.get("raw_taf"),
                timestamp=str(taf_dest.get("issue_time")) if taf_dest.get("issue_time") else now_str,
            ))

        # 6. NWS Active Weather Alerts
        for alert in nws_dest_alerts:
            evidence.append(EvidenceItem(
                source="NOAA National Weather Service",
                category="arrival_weather",
                title=f"NWS Alert: {alert.get('event')} ({destination_airport['city']})",
                severity=alert.get("severity", "medium"),
                detail=f"{alert.get('headline')}. Severity: {alert.get('severity').upper()}, Urgency: {alert.get('urgency').upper()}.",
                raw_data=f"Instruction: {alert.get('instruction')}\n\nDescription: {alert.get('description')}",
                timestamp=str(alert.get("effective")) if alert.get("effective") else now_str,
            ))

        for alert in nws_origin_alerts:
            evidence.append(EvidenceItem(
                source="NOAA National Weather Service",
                category="departure_weather",
                title=f"NWS Alert: {alert.get('event')} ({origin_airport['city']})",
                severity=alert.get("severity", "medium"),
                detail=f"{alert.get('headline')}. Impacting origin terminal airspace.",
                raw_data=alert.get("description"),
                timestamp=str(alert.get("effective")) if alert.get("effective") else now_str,
            ))

        # 7. Numerical Forecast Weather (Open-Meteo)
        if forecast_dest.get("max_wind_gust_mph", 0) >= 28:
            gust = forecast_dest["max_wind_gust_mph"]
            evidence.append(EvidenceItem(
                source="Open-Meteo High-Resolution Model",
                category="arrival_weather",
                title=f"Elevated Wind Gusts at {destination_airport['iata']}",
                severity="high" if gust >= 38 else "medium",
                detail=f"Atmospheric models predict peak surface wind gusts of {gust} mph during the travel window, increasing runway crosswind shear risk.",
                raw_data=f"Peak Wind Gust: {gust} mph | Predominant Hazard: {forecast_dest.get('predominant_hazard')}",
                timestamp=now_str,
            ))

        if forecast_dest.get("max_precip_prob", 0) >= 50:
            prob = forecast_dest["max_precip_prob"]
            evidence.append(EvidenceItem(
                source="Open-Meteo High-Resolution Model",
                category="arrival_weather",
                title=f"Precipitation & Convective Threat ({prob}%) at {destination_airport['iata']}",
                severity="high" if prob >= 75 else "medium",
                detail=f"Numerical weather models project {prob}% probability of precipitation/convective cells impacting destination runways.",
                raw_data=f"Max Precipitation Probability: {prob}%",
                timestamp=now_str,
            ))

        # 8. En-Route Corridor & Midpoint
        if airsigmets:
            convective = [s for s in airsigmets if "CONVECTIVE" in s.get("hazard", "").upper()]
            evidence.append(EvidenceItem(
                source="NOAA Aviation Weather Center",
                category="enroute",
                title=f"Active Airborne SIGMETs Across Flight Corridor ({len(airsigmets)} Active)",
                severity="high" if convective else "medium",
                detail=f"Aviation hazard advisories in effect en-route. {len(convective)} convective thunderstorm hazard zones detected.",
                raw_data=f"Sample SIGMET: {airsigmets[0].get('raw_text') if airsigmets else 'None'}",
                timestamp=now_str,
            ))

        # 9. Roadway & Highway Corridor Hazards
        if roadway_disruptions:
            for rd in roadway_disruptions:
                condition = getattr(rd, "condition_type", rd.get("condition_type") if isinstance(rd, dict) else "")
                if condition != "normal":
                    hw = getattr(rd, "highway", rd.get("highway") if isinstance(rd, dict) else "Interstate")
                    seg = getattr(rd, "segment", rd.get("segment") if isinstance(rd, dict) else "")
                    sev = getattr(rd, "severity", rd.get("severity") if isinstance(rd, dict) else "medium")
                    desc = getattr(rd, "description", rd.get("description") if isinstance(rd, dict) else "")
                    src = getattr(rd, "source", rd.get("source") if isinstance(rd, dict) else "DOT Roadway Sensors")
                    evidence.append(EvidenceItem(
                        source=src,
                        category="roadway",
                        title=f"Highway Condition: {hw} ({seg})",
                        severity=sev,
                        detail=desc,
                        raw_data=f"Highway: {hw} | Segment: {seg} | Hazard: {condition}",
                        timestamp=now_str,
                    ))

        return evidence

    @staticmethod
    def build_recommendations(
        risk_level: RiskLevel,
        composite_score: int,
        origin_airport: Dict,
        destination_airport: Dict,
        faa_dest: Dict,
        metar_dest: Optional[Dict],
        forecast_dest: Dict,
        hourly_timeline: List[Dict],
        roadway_disruptions: Optional[List[Any]] = None,
    ) -> List[ActionRecommendation]:
        """
        Formulates actionable operational guidance divided into Traveler and Operations Team actions.
        """
        recs: List[ActionRecommendation] = []

        # Find lowest-risk departure window from hourly timeline if available
        best_hour = "early morning (06:00 - 09:00)"
        if hourly_timeline:
            low_risk_hours = [h for h in hourly_timeline if h.get("disruption_score", 0) < 30]
            if low_risk_hours:
                best_hour = f"{low_risk_hours[0].get('hour_label')} - {low_risk_hours[min(3, len(low_risk_hours)-1)].get('hour_label')}"

        # 1. TRAVELER GUIDANCE - Timing
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            recs.append(ActionRecommendation(
                target="traveler",
                category="timing",
                priority="high",
                title="Target Earlier Morning Departure Flight",
                action=f"Rebook to an early departure window ({best_hour}) if possible.",
                rationale="FAA Ground Delay Programs and convective weather build up during afternoon heat, creating cascading aircraft turnaround delays. Morning flights have 65%+ higher on-time completion rates."
            ))
        elif risk_level == RiskLevel.MODERATE:
            recs.append(ActionRecommendation(
                target="traveler",
                category="timing",
                priority="medium",
                title="Maintain Flight Schedule with Airport Buffer",
                action="Arrive at departure airport 45 minutes earlier than customary.",
                rationale="Security checkpoint congestion and gate turnarounds may experience minor delays."
            ))
        else:
            recs.append(ActionRecommendation(
                target="traveler",
                category="timing",
                priority="low",
                title="Proceed as Scheduled",
                action="No schedule adjustment required.",
                rationale="Favorable weather and standard air traffic operations along this flight path."
            ))

        # 2. TRAVELER GUIDANCE - Baggage Strategy
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL) or composite_score >= 50:
            recs.append(ActionRecommendation(
                target="traveler",
                category="baggage",
                priority="high",
                title="Travel Carry-On Only (Avoid Checked Bags)",
                action="Do not check luggage; keep all vital work equipment, chargers, and overnight clothing in cabin bag.",
                rationale="During severe ground delay programs and diversions, transfer baggage separation rates surge significantly. Traveling carry-on preserves flexibility if re-routed."
            ))

        # 3. TRAVELER GUIDANCE - Ground & Corridor Alternatives (e.g. Northeast Corridor)
        orig_iata = origin_airport["iata"]
        dest_iata = destination_airport["iata"]
        ne_airports = {"JFK", "LGA", "EWR", "BOS", "PHL", "BWI", "DCA", "IAD"}
        if orig_iata in ne_airports and dest_iata in ne_airports and composite_score >= 55:
            recs.append(ActionRecommendation(
                target="traveler",
                category="routing",
                priority="high",
                title="Consider Rail Alternative (Amtrak Acela / Northeast Regional)",
                action=f"Switch from {orig_iata}→{dest_iata} flight to Amtrak Northeast Corridor rail service.",
                rationale="Northeast airspace is highly congested. Rail travel is unaffected by low ceilings, FAA slot restrictions, or runway ground stops between New York, Boston, Philadelphia, and DC."
            ))

        # 4. OPERATIONS TEAM GUIDANCE - Monitoring & Itinerary Flagging
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            recs.append(ActionRecommendation(
                target="ops_team",
                category="monitoring",
                priority="high",
                title="Flag Traveler Itinerary for Active Ops Monitoring",
                action=f"Place traveler ({origin_airport['iata']} → {destination_airport['iata']}) on high-priority watch status.",
                rationale=f"Flight has an estimated {min(95, composite_score + 10)}% likelihood of departure/arrival delay exceeding 45 minutes."
            ))

        # 5. OPERATIONS TEAM GUIDANCE - Missed Connection / Routing Policy
        if composite_score >= 55:
            recs.append(ActionRecommendation(
                target="ops_team",
                category="policy",
                priority="high",
                title="Enforce Minimum 90-Minute Connection Window",
                action="Audit traveler's itinerary for connecting legs. If connecting with less than 90 min layover, proactively re-accommodate.",
                rationale="Cascading ground delays will likely cause missed gate connections."
            ))

        # 6. OPERATIONS TEAM GUIDANCE - Airline Waiver & Duty of Care
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            recs.append(ActionRecommendation(
                target="ops_team",
                category="policy",
                priority="medium",
                title="Check for Published Airline Weather Waiver",
                action="Check airline travel advisories for published flexible change fee waivers for today/tomorrow.",
                rationale="Major carriers typically issue waivers allowing no-penalty flight changes 24 hours prior to anticipated severe weather."
            ))
            recs.append(ActionRecommendation(
                target="ops_team",
                category="duty_of_care",
                priority="medium",
                title="Pre-Authorize Lodging & Per Diem Contingency",
                action="Pre-clear overnight hotel lodging authorization if traveler is on an evening flight.",
                rationale="Late-day ground delay programs frequently roll into midnight gate crew timeouts and forced overnight stays."
            ))

        # 7. ROADWAY & STAY CONTINGENCIES (Extensible Corridor Guidance)
        if roadway_disruptions and any(getattr(r, "condition_type", getattr(r, "severity", "")) in ("chain_control", "black_ice", "blizzard", "high", "critical") for r in roadway_disruptions):
            recs.append(ActionRecommendation(
                target="traveler",
                category="stay",
                priority="high",
                title="Target Pre-Hazard Gateway Stay / Motel Refuge",
                action="Reserve room at strategic gateway lodge before entering mountain pass or winter storm sector.",
                rationale="Prevents dangerous nighttime stranding in mountain pass chain control shutdowns or freezing closures."
            ))
            recs.append(ActionRecommendation(
                target="traveler",
                category="routing",
                priority="medium",
                title="Carry Emergency Traction Chains & Winter Gear",
                action="Verify vehicle tire tread and equip emergency roadside cold-weather kit before highway transit.",
                rationale="State DOT mandates commercial/passenger traction chains during severe mountain pass weather."
            ))
            recs.append(ActionRecommendation(
                target="ops_team",
                category="policy",
                priority="medium",
                title="Authorize Emergency Roadside Rest & Lodging Expenses",
                action="Pre-approve overnight highway motel halt expenses if driving past 20:00 or during chain control.",
                rationale="Promotes driver fatigue mitigation and duty of care safety compliance."
            ))

        return recs

    @staticmethod
    def analyze_uncertainty(
        composite_score: int,
        travel_date_str: str,
        faa_dest: Dict,
        metar_dest: Optional[Dict],
        forecast_dest: Dict,
        nws_dest_alerts: List[Dict],
    ) -> UncertaintyAnalysis:
        """
        Quantifies confidence, separates confirmed ground truth from forecast variables,
        and identifies key sensitivity drivers.
        """
        confirmed = []
        variables = []
        sensitivities = []

        # Ground truth factors
        if faa_dest.get("ground_stops"):
            confirmed.append(f"FAA Ground Stop is actively confirmed in the National Airspace System for {faa_dest['airport']}.")
        elif faa_dest.get("ground_delays"):
            gd = faa_dest["ground_delays"][0]
            confirmed.append(f"FAA Ground Delay Program actively measured: {gd.get('avg_delay')} average slot delay.")
        else:
            confirmed.append(f"No FAA ground delay initiatives currently active at {faa_dest.get('airport', 'destination')}.")

        if metar_dest:
            confirmed.append(f"Destination surface flight category observed: {metar_dest.get('flight_category')} (Visibility: {metar_dest.get('visibility_sm')}SM, Ceiling: {metar_dest.get('ceiling_ft') or 'Unlimited'}ft).")

        # Forecast variables
        if travel_date_str == "today":
            variables.append("Same-day travel window: Real-time telemetry carries high weight, but intra-day convective storm initiation timing can vary +/- 60 minutes.")
        else:
            variables.append("Next-day forward assessment: Atmospheric frontal movement speed has a +/- 2 to 3 hour variance window.")
            
        if forecast_dest.get("max_precip_prob", 0) > 0:
            variables.append(f"Precipitation probability is model-estimated at {forecast_dest.get('max_precip_prob')}%.")

        if forecast_dest.get("max_wind_gust_mph", 0) > 20:
            variables.append(f"Surface wind gusts modeled up to {forecast_dest.get('max_wind_gust_mph')} mph (subject to localized thermal shear).")

        # Sensitivity drivers
        sensitivities.append("Runway Configuration Threshold: If crosswinds exceed 20 kts at destination, airport capacity drops 35-50% as runways are taken offline.")
        sensitivities.append("Low Ceiling Persistence: If morning cloud deck/fog burns off 1 hour earlier than forecasted, ground delay programs will lift quickly.")
        sensitivities.append("Airline Turnaround Cascades: Inbound aircraft originating from severe weather hubs (e.g. ORD, DFW) may cause delay even if local route weather is clear.")

        # Calculate confidence score
        if travel_date_str == "today":
            confidence_score = 90 if faa_dest.get("has_disruption") else 85
            confidence_tier = "High Confidence (Real-Time Sensor Ground Truth)"
        else:
            confidence_score = 78
            confidence_tier = "Moderate Confidence (Numerical Model Blend + TAF Outlook)"

        return UncertaintyAnalysis(
            confidence_score=confidence_score,
            confidence_tier=confidence_tier,
            confirmed_factors=confirmed,
            forecast_variables=variables,
            sensitivity_drivers=sensitivities,
        )

    @staticmethod
    def generate_briefing(
        route_summary: Dict,
        risk_level: RiskLevel,
        composite_score: int,
        verdict: str,
        delay_prob: int,
        expected_delay: str,
        evidence: List[EvidenceItem],
        uncertainty: UncertaintyAnalysis,
    ) -> str:
        """
        Synthesizes a clean, high-density executive operational briefing.
        """
        orig = route_summary["origin"]["iata"]
        dest = route_summary["destination"]["iata"]
        date_str = route_summary.get("travel_date", "upcoming")
        
        briefing = f"""### EXECUTIVE OPERATIONAL BRIEFING: {orig} → {dest} ({date_str.upper()})

**OVERALL STATUS: {risk_level.value} DISRUPTION RISK (Score: {composite_score}/100)**
{verdict}

**PROBABILISTIC IMPACT PROFILE:**
- **Departure/Arrival Delay Likelihood:** {delay_prob}%
- **Expected Delay Magnitude:** {expected_delay}
- **Assessment Confidence:** {uncertainty.confidence_score}% ({uncertainty.confidence_tier})

**KEY EVIDENCE SIGNALS:**
"""
        # Highlight top 3 evidence items
        top_evidence = [e for e in evidence if e.severity in ("critical", "high")][:3]
        if not top_evidence:
            top_evidence = evidence[:3]

        for e in top_evidence:
            briefing += f"- **[{e.source}]** {e.title}: {e.detail}\n"

        briefing += f"""
**OPERATIONAL UNCERTAINTY & DECISION THRESHOLDS:**
{uncertainty.sensitivity_drivers[0]}
"""
        return briefing.strip()
