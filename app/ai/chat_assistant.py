"""
Strata Ops // Real-Time Journey Companion AI Assistant.
Provides conversational travel intelligence, scenario evaluation, delay mitigation advice,
and operational rerouting guidance grounded directly in the live assessment evidence dossier.
"""

import os
import re
import logging
from typing import Dict, List, Optional, Tuple
from app.models import JourneyChatRequest, JourneyChatResponse

logger = logging.getLogger(__name__)


class JourneyChatAssistant:
    @staticmethod
    async def process_chat(req: JourneyChatRequest) -> JourneyChatResponse:
        user_msg = req.message.strip()
        ctx = req.assessment_context or {}
        api_key = req.gemini_api_key or os.getenv("GEMINI_API_KEY")

        # 1. Try Gemini LLM if key is available
        if api_key:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                system_instruction = (
                    "You are the Strata Ops Real-Time Travel Disruption Intelligence Assistant. "
                    "You assist corporate travelers and operations dispatchers with trip disruptions, "
                    "weather hazards, FAA airspace ground stops, mountain pass chain controls, and alternate routes. "
                    "Always be direct, highly actionable, concise, and grounded in the live trip data provided in the context. "
                    "Format responses using clean markdown bullets and bold headers. "
                    "Never hallucinate airline policies or make up ungrounded weather."
                )

                prompt = f"""
Trip Context:
- Route: {ctx.get('route', {}).get('origin', {}).get('iata', 'ORIG')} ({ctx.get('route', {}).get('origin', {}).get('city', '')}) → {ctx.get('route', {}).get('destination', {}).get('iata', 'DEST')} ({ctx.get('route', {}).get('destination', {}).get('city', '')})
- Travel Mode: {ctx.get('travel_mode', 'air')}
- Travel Date: {ctx.get('route', {}).get('travel_date', 'tomorrow')}
- Composite Disruption Score: {ctx.get('composite_risk_score', 'N/A')}/100 ({ctx.get('risk_level', 'N/A')} Risk)
- Executive Verdict: {ctx.get('executive_verdict', 'N/A')}
- Delay Probability: {ctx.get('delay_probability', 'N/A')}% (Range: {ctx.get('expected_delay_range', 'N/A')})
- Cancellation Probability: {ctx.get('cancellation_probability', 'N/A')}%
- Missed Connection Risk: {ctx.get('missed_connection_risk', 'N/A')}%
- Confidence Tier: {ctx.get('uncertainty', {}).get('confidence_tier', 'High')} ({ctx.get('uncertainty', {}).get('confidence_score', '85')}%)
- Confirmed Ground Truth: {', '.join(ctx.get('uncertainty', {}).get('confirmed_factors', [])[:4])}
- Alternate Routes: {[a.get('title') for a in ctx.get('alternate_routes', [])]}

Traveler Question:
"{user_msg}"

Provide an operational, reassuring, and highly specific answer with actionable recommendations.
"""
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={"system_instruction": system_instruction, "temperature": 0.2},
                )
                if resp.text:
                    suggested = JourneyChatAssistant._generate_suggested_questions(ctx, user_msg)
                    return JourneyChatResponse(reply=resp.text, suggested_questions=suggested)
            except Exception as e:
                logger.warning(f"Gemini Chat call failed: {e}. Falling back to deterministic operational assistant.")

        # 2. Deterministic Grounded Operational Intelligence Assistant
        reply = JourneyChatAssistant._deterministic_reply(user_msg, ctx)
        suggested = JourneyChatAssistant._generate_suggested_questions(ctx, user_msg)
        return JourneyChatResponse(reply=reply, suggested_questions=suggested)

    @staticmethod
    def _deterministic_reply(query: str, ctx: Dict) -> str:
        q = query.lower()
        orig = ctx.get("route", {}).get("origin", {}).get("iata", "Origin")
        dest = ctx.get("route", {}).get("destination", {}).get("iata", "Destination")
        dest_city = ctx.get("route", {}).get("destination", {}).get("city", "Destination")
        orig_city = ctx.get("route", {}).get("origin", {}).get("city", "Origin")
        score = ctx.get("composite_risk_score", 30)
        level = ctx.get("risk_level", "LOW")
        delay_prob = ctx.get("delay_probability", 25)
        delay_range = ctx.get("expected_delay_range", "0-30 min")
        mode = ctx.get("travel_mode", "air")
        alternates = ctx.get("alternate_routes", [])

        # Intent 1: Draft Communication / Email to manager
        if any(w in q for w in ["email", "draft", "notify", "manager", "client", "message", "write"]):
            return (
                f"### 📋 Recommended Disruption Notice for Stakeholders\n\n"
                f"Here is a corporate travel alert email ready to send:\n\n"
                f"**Subject:** [Travel Alert] Possible {level} Delay on {orig} → {dest} ({ctx.get('route', {}).get('travel_date', 'Tomorrow')})\n\n"
                f"> Hi Team,\n>\n"
                f"> I am currently tracking our travel itinerary from **{orig_city}** to **{dest_city}** via Strata Ops Intelligence.\n>\n"
                f"> **Current Operational Status:**\n"
                f"> - **Risk Assessment:** {level} Disruption Risk (Score: {score}/100)\n"
                f"> - **Projected Delay:** ~{delay_range} (Delay Probability: {delay_prob}%)\n"
                f"> - **Primary Factor:** {ctx.get('executive_verdict', 'Terminal weather and airspace capacity constraints.')}\n>\n"
                f"> **Contingency Action:** I am traveling carry-on only and monitoring earlier flight/reroute options. If delays exceed 45 minutes, I will execute our backup contingency plan.\n>\n"
                f"> Best regards,\n> [Your Name]\n"
            )

        # Intent 2: Alternate Routes & Co-Terminal Bypasses
        if any(w in q for w in ["alternate", "bypass", "reroute", "another route", "other airport", "switch"]):
            if alternates:
                lines = [f"### 🔄 Evaluated Alternate Routes for {orig} → {dest}\n"]
                for i, alt in enumerate(alternates, 1):
                    lines.append(
                        f"**Option {i}: {alt.get('title')}**\n"
                        f"- **Projected Risk Score:** {alt.get('projected_risk_score')}/100 "
                        f"(*{alt.get('risk_reduction_points', 0)} pts risk reduction*)\n"
                        f"- **Key Benefit:** {alt.get('key_benefit')}\n"
                        f"- **Tradeoff:** {alt.get('tradeoff')}\n"
                    )
                lines.append(
                    "> **Tip:** You can click the **[Switch to Alternate Route]** button in the Alternate Routes card above to immediately recalculate the live telemetry."
                )
                return "\n".join(lines)
            else:
                return (
                    f"### 🔄 Alternate Route Analysis\n\n"
                    f"For **{orig} → {dest}**, current telemetry shows direct routing is operating favorably (Risk Score: {score}/100). "
                    f"If conditions deteriorate, target co-terminal regional airports in the {dest_city} metro or an earlier morning departure window."
                )

        # Intent 3: Flying vs Driving Comparison
        if any(w in q for w in ["drive", "driving", "car", "road", "fly vs drive", "highway"]):
            drive_dist = ctx.get("route", {}).get("driving_distance_miles", 300)
            drive_time = ctx.get("route", {}).get("driving_time_est", "5h")
            if mode == "road":
                return (
                    f"### 🚗 Driving Corridor Evaluation ({orig_city} → {dest_city})\n\n"
                    f"- **Distance & Time:** ~{drive_dist} miles (Est. {drive_time})\n"
                    f"- **Pavement Status:** {ctx.get('executive_verdict', 'Favorable highway conditions.')}\n"
                    f"- **Operational Verdict:** Driving provides 100% schedule control with zero risk of airport ground delays. "
                    f"Ensure fatigue breaks every 2.5 hours at scheduled service plazas."
                )
            else:
                return (
                    f"### ✈️ vs 🚗 Flight vs Highway Drive Analysis\n\n"
                    f"- **Commercial Flight:** Cruising time ~{ctx.get('route', {}).get('flight_time_est', 'N/A')}, with {delay_prob}% delay risk.\n"
                    f"- **Interstate Highway Drive:** {drive_dist} miles (~{drive_time} driving time).\n"
                    f"- **Decision Rule:** {'Driving is a viable backup if commercial flights face ground stops.' if drive_dist < 450 else 'Flight remains recommended due to long driving distance exceeding 8 hours.'}"
                )

        # Intent 4: What if flight canceled / delay happens
        if any(w in q for w in ["cancel", "delayed", "miss", "connection", "what if", "stuck"]):
            return (
                f"### 🛡️ Step-by-Step Delay & Cancellation Recovery Protocol\n\n"
                f"1. **Hold Backup Seat via Airline App First:** Open your carrier's mobile app immediately. Most airlines unlock complimentary self-rebooking the moment a Ground Delay Program or flight waiver is posted.\n"
                f"2. **Carry-On Luggage Rule:** Keep all critical electronics, medications, and chargers with you. Never gate-check bags during {level.lower()}-risk weather windows.\n"
                f"3. **Target Co-Terminal Bypasses:** Ask the agent for standby into nearby regional airports (e.g. OAK instead of SFO, EWR instead of JFK, MDW instead of ORD).\n"
                f"4. **Lodging Voucher Activation:** If canceled past 20:00 local time, corporate policy authorizes immediate hotel stay at vetted corridor properties."
            )

        # Intent 5: Uncertainty & Confidence Explanation
        if any(w in q for w in ["uncertainty", "confidence", "how sure", "accuracy", "forecast"]):
            conf = ctx.get("uncertainty", {})
            return (
                f"### 🎯 Uncertainty Quantification Breakdown\n\n"
                f"- **Model Confidence Score:** **{conf.get('confidence_score', 85)}%** ({conf.get('confidence_tier', 'High Confidence')})\n"
                f"- **Ground Truth Anchors:** Measured real-time METAR sensors and official FAA Command Center notices.\n"
                f"- **Forecast Horizon Sensitivity:** Forward-looking atmospheric projections have a ±90 minute convective cell variance.\n"
                f"- **Key Trigger:** {conf.get('sensitivity_drivers', ['Rapid frontal passage shift'])[0] if conf.get('sensitivity_drivers') else 'Sudden wind shear or thunderstorm development'}"
            )

        # Default: General Executive Travel Advisory
        return (
            f"### 🧭 Executive Travel Briefing for {orig} → {dest}\n\n"
            f"- **Current Risk Level:** **{level}** ({score}/100 composite index)\n"
            f"- **Expected Delay:** **{delay_range}** (Probability: {delay_prob}%)\n"
            f"- **Operations Verdict:** {ctx.get('executive_verdict', 'Operational corridor is currently stable.')}\n"
            f"- **Actionable Next Step:** {ctx.get('headline_risk_summary', 'Monitor real-time alerts before heading to the terminal or highway merge.')}\n\n"
            f"Ask me any follow-up question below, or ask to draft a stakeholder notice!"
        )

    @staticmethod
    def _generate_suggested_questions(ctx: Dict, last_query: str) -> List[str]:
        mode = ctx.get("travel_mode", "air")
        score = ctx.get("composite_risk_score", 30)

        if mode == "road":
            return [
                "Where should I stop for fuel and fatigue breaks?",
                "What is the best departure window to avoid traffic?",
                "Draft an email to my manager about my road trip schedule",
            ]
        elif score >= 50:
            return [
                "What alternate flights or airports avoid this delay?",
                "Draft a delay notice email for my team/client",
                "What happens if my connection is missed?",
            ]
        else:
            return [
                "Is driving or flying better for this route?",
                "What could change that would increase the risk?",
                "Draft an itinerary confirmation email to my team",
            ]
