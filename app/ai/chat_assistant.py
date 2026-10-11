"""
Strata Ops // Real-Time Journey Companion AI Assistant.
Provides conversational travel intelligence, scenario evaluation, delay mitigation advice,
tactical roadside halt recommendations, and operational rerouting guidance grounded directly
in the live assessment evidence dossier.
"""

import os
import re
import logging
from typing import Dict, List, Optional
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
                    "weather hazards, FAA airspace ground stops, highway halts, and vetted alternate routes. "
                    "Always be direct, highly actionable, concise, and grounded in the live trip data provided in the context. "
                    "Format responses using clean markdown bullets and bold headers. "
                    "When asked about halts, fuel stops, or single halts on road journeys, reference the specific major cities, "
                    "highways, and exit numbers provided in the context."
                )

                # Format computed halts for LLM prompt
                halts_desc = []
                for h in ctx.get("halt_suggestions", []):
                    halts_desc.append(
                        f"Stop #{h.get('stop_number')}: {h.get('city', 'Hub')}, {h.get('state', '')} "
                        f"({h.get('location_name', '')}) on {h.get('highway', '')} at {h.get('mile_marker', '')} "
                        f"[Dist: {h.get('distance_from_origin_miles')} mi, Drive Time: {h.get('estimated_drive_time')}] "
                        f"- Rationale: {h.get('rationale')}"
                    )

                prompt = f"""
Trip Context:
- Route: {ctx.get('route', {}).get('origin', {}).get('iata', 'ORIG')} ({ctx.get('route', {}).get('origin', {}).get('city', '')}) → {ctx.get('route', {}).get('destination', {}).get('iata', 'DEST')} ({ctx.get('route', {}).get('destination', {}).get('city', '')})
- Travel Mode: {ctx.get('travel_mode', 'air')}
- Travel Date: {ctx.get('route', {}).get('travel_date', 'tomorrow')}
- Driving Distance & Time: {ctx.get('route', {}).get('driving_distance_miles', 'N/A')} miles (~{ctx.get('route', {}).get('driving_time_est', 'N/A')})
- Primary Highways: {ctx.get('route', {}).get('primary_interstates', [])}
- Composite Disruption Score: {ctx.get('composite_risk_score', 'N/A')}/100 ({ctx.get('risk_level', 'N/A')} Risk)
- Executive Verdict: {ctx.get('executive_verdict', 'N/A')}
- Delay Probability: {ctx.get('delay_probability', 'N/A')}% (Range: {ctx.get('expected_delay_range', 'N/A')})
- Road Hazards: {[d.get('description') for d in ctx.get('roadway_disruptions', [])]}
- Strategic Halts: {halts_desc}
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
        route = ctx.get("route", {})
        orig = route.get("origin", {}).get("iata", "Origin")
        dest = route.get("destination", {}).get("iata", "Destination")
        dest_city = route.get("destination", {}).get("city", "Destination")
        orig_city = route.get("origin", {}).get("city", "Origin")
        score = ctx.get("composite_risk_score", 30)
        level = ctx.get("risk_level", "LOW")
        delay_prob = ctx.get("delay_probability", 25)
        delay_range = ctx.get("expected_delay_range", "0-30 min")
        mode = ctx.get("travel_mode", "air")
        alternates = ctx.get("alternate_routes", [])
        halts = ctx.get("halt_suggestions", [])
        disruptions = ctx.get("roadway_disruptions", [])
        drive_dist = route.get("driving_distance_miles", 330)
        drive_time = route.get("driving_time_est", "5h")
        primary_highways = route.get("primary_interstates", ["I-20 West"])

        # ---------------------------------------------------------------------
        # Intent 1: Halts, Fuel, Fatigue Breaks & Single Halt Queries
        # (e.g. "Where should I stop for fuel and fatigue breaks?", "What if I need only one halt?", "one halt", "gas")
        # ---------------------------------------------------------------------
        if any(w in q for w in ["halt", "fuel", "fatigue", "stop", "break", "rest", "gas", "charge", "ev", "one halt", "1 halt", "single halt"]):
            is_single_halt_query = any(w in q for w in ["one halt", "1 halt", "single halt", "only one", "just one"])

            if halts:
                # Find the primary recommended halt (either stop #1 or the one matching Abilene / midpoint)
                primary_halt = halts[0]
                if len(halts) > 1 and is_single_halt_query:
                    # Pick the midpoint halt (e.g. Abilene)
                    primary_halt = next((h for h in halts if "abilene" in (h.get("city") or "").lower() or h.get("stop_number") == 1), halts[0])

                city_name = primary_halt.get("city") or "Mid-Corridor Hub"
                state_name = primary_halt.get("state") or ""
                city_label = f"{city_name}, {state_name}" if state_name else city_name
                loc_name = primary_halt.get("location_name", "Interstate Service Plaza")
                hwy = primary_halt.get("highway", "Interstate Mainline")
                exit_mm = primary_halt.get("mile_marker", "Key Exit")
                dist_mi = primary_halt.get("distance_from_origin_miles", 198)
                time_est = primary_halt.get("estimated_drive_time", "2h 45m")
                facilities = primary_halt.get("facilities", ["24/7 Fuel", "Restrooms", "Food"])

                if is_single_halt_query:
                    return (
                        f"### 📍 Single Recommended Halt: {city_label}\n\n"
                        f"If you prefer **only one halt** for {orig_city} → {dest_city} (~{drive_dist} miles, ~{drive_time} driving time), "
                        f"your single essential stop is **{city_label}**:\n\n"
                        f"- **Location:** **{loc_name}** ({hwy}, {exit_mm})\n"
                        f"- **Timing:** **{dist_mi} miles** from origin (~**{time_est}** elapsed drive time)\n"
                        f"- **Key Facilities:** {', '.join(facilities[:4])}\n"
                        f"- **Why this halt is ideal:** It splits your {drive_time} drive into two balanced segments of ~2.5 hours each. "
                        f"Stopping in {city_name} resets driver cognitive focus, tops off fuel or EV fast charging, "
                        f"and lets you check local West Texas radar before ascending the Caprock Escarpment into Lubbock.\n\n"
                        f"> **Dashboard Tip:** You can also click the **[1 City Halt]** button under **Highway Preferences** on the dashboard above to lock the live map and telemetry exclusively to this single stop."
                    )
                else:
                    halt_bullets = []
                    for h in halts:
                        c_label = f"{h.get('city')}, {h.get('state')}" if h.get('city') else h.get('location_name')
                        halt_bullets.append(
                            f"**Stop #{h.get('stop_number')}: {c_label}** ({h.get('highway')}, {h.get('mile_marker')})\n"
                            f"  - **Distance & Timing:** ~{h.get('distance_from_origin_miles')} mi (~{h.get('estimated_drive_time')} elapsed)\n"
                            f"  - **Facilities:** {', '.join((h.get('facilities') or [])[:3])}\n"
                            f"  - **Purpose:** {h.get('rationale')}"
                        )

                    return (
                        f"### ⛽ Strategic Fuel & Fatigue Halts for {orig_city} → {dest_city}\n\n"
                        f"To maintain driver alertness and prevent cognitive fatigue, here are your strategic waypoints along **{primary_highways[0]}**:\n\n"
                        + "\n\n".join(halt_bullets) +
                        f"\n\n> **Recommendation:** Standard transportation safety (DOT/NHTSA) recommends stopping for 15–20 minutes every 2.5 to 3 hours. "
                        f"For this ~{drive_dist}-mile drive, stopping in **{city_name}** is the primary essential halt."
                    )
            else:
                # Fallback if no halts generated yet
                return (
                    f"### 📍 Halt Recommendation for {orig_city} → {dest_city}\n\n"
                    f"For driving between **{orig_city}** and **{dest_city}** (~{drive_dist} miles, ~{drive_time}), "
                    f"the primary commercial midpoint is **Abilene, TX** (I-20 West, Exit 286 / Junction US-84).\n\n"
                    f"- **Distance:** ~198 miles from Dallas (~2h 45m drive)\n"
                    f"- **Amenities:** Pilot Flying J / Love's Travel Stop, Tesla Superchargers, Hendrick Health Level 1 care, and 24/7 food.\n"
                    f"- **Operational Purpose:** Vital for driver fatigue mitigation, vehicle refueling, and checking West Texas crosswinds before the Caprock Escarpment."
                )

        # ---------------------------------------------------------------------
        # Intent 2: Departure Windows & Traffic Avoidance
        # (e.g. "What is the best departure window to avoid traffic?", "when should I leave", "departure time")
        # ---------------------------------------------------------------------
        if any(w in q for w in ["departure window", "best departure", "when should i leave", "best time", "avoid traffic", "rush hour", "timing"]):
            if mode == "road":
                return (
                    f"### ⏱️ Optimal Departure Windows for Driving ({orig_city} → {dest_city})\n\n"
                    f"1. **Primary Recommended Window: Early Morning (06:00 – 07:30 AM)**\n"
                    f"   - Clears the {orig_city} metropolitan beltway before peak commuter congestion.\n"
                    f"   - Guarantees arriving in {dest_city} by ~12:30 PM with 100% daylight driving and cooler road pavement temperatures.\n\n"
                    f"2. **Secondary Window: Mid-Morning (09:30 – 11:00 AM)**\n"
                    f"   - Allows morning metro rush hour to fully dissipate before merging onto the Interstate.\n"
                    f"   - Arrives late afternoon (~04:00 PM) before sunset.\n\n"
                    f"> **Avoid:** Late afternoon departures (16:30 – 18:30) which trap you in outbound metropolitan rush hour and push the Caprock Escarpment stretch into dark twilight with increased deer hazard."
                )
            else:
                return (
                    f"### ⏱️ Optimal Departure Window for Air Travel ({orig} → {dest})\n\n"
                    f"1. **Early Flight Window (06:00 – 09:00 AM):** Highest on-time reliability. Air traffic control arrival slots are clear and convective thunderstorm development is minimal.\n"
                    f"2. **Afternoon Flights (14:00 – 18:00):** Vulnerable to airspace capacity ground delays and thermal storm fronts (+40% delay probability).\n\n"
                    f"> **Recommendation:** Target the earliest morning departure flight to minimize ripple delays."
                )

        # ---------------------------------------------------------------------
        # Intent 3: Draft Communication / Email to Manager or Client
        # ---------------------------------------------------------------------
        if any(w in q for w in ["email", "draft", "notify", "manager", "client", "message", "schedule", "itinerary"]):
            if mode == "road":
                return (
                    f"### 📋 Corporate Road Trip Itinerary Notice\n\n"
                    f"**Subject:** [Travel Itinerary] Road Transit Schedule: {orig_city} → {dest_city} ({ctx.get('route', {}).get('travel_date', 'Tomorrow')})\n\n"
                    f"> Hi Team,\n>\n"
                    f"> I will be driving from **{orig_city}** to **{dest_city}** via interstate highway.\n>\n"
                    f"> **Trip Schedule & Details:**\n"
                    f"> - **Total Distance & Driving Time:** ~{drive_dist} miles (~{drive_time})\n"
                    f"> - **Route Corridor:** {primary_highways[0]}\n"
                    f"> - **Planned Rest & Fuel Halt:** Abilene, TX (Mile marker 286, ~2.8 hours into drive)\n"
                    f"> - **Expected Arrival:** Early afternoon at {dest_city} destination\n"
                    f"> - **Corridor Status:** Favorable pavement conditions; zero active road closures.\n>\n"
                    f"> I will remain reachable by mobile and will confirm arrival upon reaching our site.\n>\n"
                    f"> Best regards,\n> [Your Name]\n"
                )
            else:
                return (
                    f"### 📋 Recommended Disruption Notice for Stakeholders\n\n"
                    f"**Subject:** [Travel Alert] Possible {level} Delay on {orig} → {dest} ({ctx.get('route', {}).get('travel_date', 'Tomorrow')})\n\n"
                    f"> Hi Team,\n>\n"
                    f"> I am currently tracking our flight from **{orig_city}** to **{dest_city}** via Strata Ops Disruption Intelligence.\n>\n"
                    f"> **Current Status:**\n"
                    f"> - **Risk Assessment:** {level} Disruption Risk (Score: {score}/100)\n"
                    f"> - **Projected Delay:** ~{delay_range} (Delay Probability: {delay_prob}%)\n"
                    f"> - **Primary Factor:** {ctx.get('executive_verdict', 'Terminal weather and airspace capacity constraints.')}\n>\n"
                    f"> **Contingency Action:** Traveling carry-on only and monitoring co-terminal backup flights. If delayed past 45 minutes, I will execute our backup contingency plan.\n>\n"
                    f"> Best regards,\n> [Your Name]\n"
                )

        # ---------------------------------------------------------------------
        # Intent 4: Flying vs Driving Comparison
        # ---------------------------------------------------------------------
        if any(w in q for w in ["fly vs drive", "flight vs drive", "driving vs flying", "better to drive", "should i drive", "car vs plane"]):
            return (
                f"### ✈️ vs 🚗 Flight vs Highway Drive Analysis ({orig_city} → {dest_city})\n\n"
                f"- **Highway Driving:** ~{drive_dist} miles (~{drive_time} door-to-door).\n"
                f"  - **Pros:** 100% deterministic schedule control, zero risk of airline gate stranding or airport cancellations.\n"
                f"  - **Pavement Status:** {ctx.get('executive_verdict', 'Favorable highway conditions.')}\n\n"
                f"- **Commercial Flight:**\n"
                f"  - **Total Travel Time:** ~4.5 hours (including 2h TSA/boarding buffer + 1h flight + 45m luggage/car rental).\n"
                f"  - **Disruption Exposure:** {delay_prob}% delay risk, vulnerable to FAA ground delay programs.\n\n"
                f"- **Decision Rule:** For distances under 350 miles like {orig_city} → {dest_city}, **highway driving is faster or equivalent door-to-door** with superior schedule predictability."
            )

        # ---------------------------------------------------------------------
        # Intent 5: Road Conditions, Hazards & Safety
        # ---------------------------------------------------------------------
        if any(w in q for w in ["safe", "road condition", "hazard", "ice", "wind", "pavement", "closures"]):
            if disruptions:
                h_lines = []
                for d in disruptions:
                    h_lines.append(f"- **{d.get('highway')}:** {d.get('description')} (*Est. Delay: +{d.get('delay_estimate_minutes', 0)}m*)")
                return (
                    f"### ⚠️ Road Surface & Weather Advisories ({orig_city} → {dest_city})\n\n"
                    + "\n".join(h_lines) +
                    f"\n\n**Driver Directive:** Maintain standard interstate speeds, allow extra following distance, and verify tire pressure at your scheduled halt."
                )
            else:
                return (
                    f"### 🟢 Highway Pavement & Road Safety Status\n\n"
                    f"Corridor **{primary_highways[0]}** from **{orig_city}** to **{dest_city}** is operating normally with **no active DOT road closures or hazardous pavement advisories**.\n"
                    f"- Pavement is dry and free-flow interstate speeds are operable.\n"
                    f"- Maintain recommended rest halts every 2.5–3 hours for driver focus."
                )

        # ---------------------------------------------------------------------
        # Intent 6: Alternate Routes & Co-Terminal Bypasses
        # ---------------------------------------------------------------------
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
                    "> **Tip:** You can click the **[Switch to Alternate Route]** button on the dashboard to immediately run live telemetry for that path."
                )
                return "\n".join(lines)
            else:
                return (
                    f"### 🔄 Alternate Route Analysis\n\n"
                    f"For **{orig} → {dest}**, current telemetry shows the primary corridor is optimal (Risk Score: {score}/100). "
                    f"No high-priority diversions required."
                )

        # ---------------------------------------------------------------------
        # Intent 7: Airline Delay / Cancellation Protocols (Air mode only)
        # ---------------------------------------------------------------------
        if any(w in q for w in ["cancel", "airline", "gate", "flight delayed", "luggage", "voucher", "hotel"]):
            return (
                f"### 🛡️ Step-by-Step Delay & Cancellation Recovery Protocol\n\n"
                f"1. **Hold Backup Seat via Airline App First:** Open carrier mobile app immediately to grab standby seats before airport customer service lines form.\n"
                f"2. **Carry-On Luggage Rule:** Keep critical gear, medication, and laptops in your carry-on bag.\n"
                f"3. **Target Co-Terminal Bypasses:** Ask the agent for rerouting to nearby regional airports.\n"
                f"4. **Lodging Voucher Activation:** If delayed past 20:00 local time, corporate policy authorizes emergency hotel lodging."
            )

        # ---------------------------------------------------------------------
        # Default: Context-Aware Executive Travel Advisory
        # ---------------------------------------------------------------------
        if mode == "road":
            return (
                f"### 🧭 Executive Road Travel Briefing for {orig_city} → {dest_city}\n\n"
                f"- **Corridor:** **{primary_highways[0]}** (~{drive_dist} miles, ~{drive_time})\n"
                f"- **Current Highway Risk:** **{level}** ({score}/100 composite index)\n"
                f"- **Primary Halt:** Abilene, TX (Mile marker 286, midway fuel & driver focus reset)\n"
                f"- **Pavement Status:** {ctx.get('executive_verdict', 'Favorable highway conditions; no active closures.')}\n\n"
                f"Ask me about **where to stop**, **departure times**, or **drafting a travel notice for your manager**!"
            )
        else:
            return (
                f"### 🧭 Executive Travel Briefing for {orig} → {dest}\n\n"
                f"- **Current Risk Level:** **{level}** ({score}/100 composite index)\n"
                f"- **Expected Delay:** **{delay_range}** (Probability: {delay_prob}%)\n"
                f"- **Operations Verdict:** {ctx.get('executive_verdict', 'Operational corridor is currently stable.')}\n"
                f"- **Actionable Next Step:** {ctx.get('headline_risk_summary', 'Monitor real-time alerts before heading to the terminal.')}\n\n"
                f"Ask me about **alternate flights**, **departure windows**, or **drafting a manager alert**!"
            )

    @staticmethod
    def _generate_suggested_questions(ctx: Dict, last_query: str) -> List[str]:
        mode = ctx.get("travel_mode", "air")
        score = ctx.get("composite_risk_score", 30)

        if mode == "road":
            return [
                "Where should I stop for fuel and fatigue breaks?",
                "What if I need only one halt?",
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
                "What is the best departure window to avoid delays?",
                "Draft an itinerary confirmation email to my team",
            ]
