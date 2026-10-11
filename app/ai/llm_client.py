"""
Google Gemini LLM Integration for Advanced Operational Synthesis.
Uses the official google-genai SDK to generate rich executive briefings,
probabilistic reasoning over conflicting signals, and counterfactual travel guidance.
"""

import os
import logging
from typing import Dict, List, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiAIClient:
    @staticmethod
    def is_available(custom_key: Optional[str] = None) -> bool:
        """
        Checks whether a Gemini API key is configured.
        """
        key = custom_key or os.getenv("GEMINI_API_KEY")
        return bool(key and key.strip())

    @staticmethod
    async def generate_synthesis(
        route_summary: Dict,
        composite_score: int,
        risk_level: str,
        delay_prob: int,
        expected_delay: str,
        evidence: List[Dict],
        uncertainty: Dict,
        custom_key: Optional[str] = None,
    ) -> Optional[str]:
        """
        Synthesizes a high-level operational intelligence briefing using Gemini 2.5 Flash.
        """
        api_key = (custom_key or os.getenv("GEMINI_API_KEY") or "").strip()
        if not api_key:
            return None

        orig = route_summary["origin"]["iata"]
        dest = route_summary["destination"]["iata"]
        travel_date = route_summary.get("travel_date", "upcoming")
        
        # Build prompt with telemetry facts
        evidence_text = "\n".join([
            f"- [{e.get('source')}] ({e.get('category')}) {e.get('title')}: {e.get('detail')} (Raw: {e.get('raw_data', '')[:120]})"
            for e in evidence[:8]
        ])

        prompt = f"""You are the Chief Travel Risk Officer for a corporate operations center managing travel for frequent business travelers across the United States.

Evaluate the following multi-signal telemetry for an upcoming corporate trip:
- Route: {orig} ({route_summary['origin']['city']}) → {dest} ({route_summary['destination']['city']})
- Travel Date: {travel_date}
- Flight Distance: {route_summary.get('distance_miles')} miles (Estimated air time: {route_summary.get('flight_time_est')})
- Computed Disruption Risk Score: {composite_score}/100 ({risk_level})
- Statistical Delay Likelihood: {delay_prob}%
- Projected Delay Duration: {expected_delay}

REAL-TIME SENSOR & AGENCY TELEMETRY:
{evidence_text}

UNCERTAINTY & SENSITIVITY CONTEXT:
- Confirmed Facts: {', '.join(uncertainty.get('confirmed_factors', []))}
- Model Forecast Variables: {', '.join(uncertainty.get('forecast_variables', []))}
- Key Sensitivity Triggers: {', '.join(uncertainty.get('sensitivity_drivers', []))}

TASK:
Produce a concise, high-impact Operational Disruption Briefing in GitHub-flavored Markdown for both the Operations Center and the Corporate Traveler.
Include:
1. **Executive Verdict**: Clear bottom-line judgment on whether this trip faces meaningful disruption risk.
2. **Root Disruption Drivers**: Synthesize the interplay between the FAA airspace programs, terminal meteorology, and en-route corridor hazards (do not simply list them; explain *how* they interact).
3. **Uncertainty & Decision Thresholds**: Explicitly articulate what is known with high certainty vs what is subject to variance, and what environmental shift (e.g., wind shift, fog burn-off) would flip the risk profile.
4. **Actionable Operations Matrix**:
   - For Traveler: Specific departure window, baggage advice, ground transit buffer.
   - For Ops Team: Connection risk alerts, airline waiver monitoring, duty of care protocols.

Keep your tone professional, decisive, analytical, and authoritative. Do not invent fake flights. Focus strictly on operational risk intelligence.
"""

        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=1000,
                ),
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}. Falling back to built-in intelligence engine.")
            return None

        return None
