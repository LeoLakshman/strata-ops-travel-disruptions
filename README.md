---
title: Strata Ops - U.S. Travel Disruption Intelligence
emoji: ✈️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Strata Ops // U.S. Corporate Travel Disruption Intelligence

> **One intelligent dashboard for corporate travel operations: real-time multi-source risk assessment, evidence traceability, and operational decision support.**

---

## 1. Executive Summary & Problem Framing

Corporate travel operations teams face a recurring friction point: when employees travel across the United States, critical information about potential disruptions is fragmented across half a dozen incompatible systems:
- The **FAA Command Center (ATCSCC)** for air traffic management initiatives and ground delay programs.
- The **National Weather Service (NWS)** for severe weather warnings, watches, and advisories.
- The **Aviation Weather Center (AWC)** for coded METAR surface observations and TAF terminal aerodrome forecasts.
- Numerical weather models for hour-by-hour forward-looking precipitation and wind profiles.
- Airline portals and commercial flight trackers.

By the time an operations coordinator checks all these sources, the flight may already be delayed, connections missed, and employees stranded.

**Strata Ops** solves this by unifying **four live, real-time government and atmospheric telemetry feeds** into a single cognitive intelligence platform. It assesses any U.S. domestic route and travel date (e.g., *New York → San Francisco, tomorrow*), calculates calibrated disruption probabilities, traces every risk to its underlying raw sensor evidence, articulates uncertainty, and outputs actionable guidance for both the traveler and the operations desk.

---

## 2. Live External Data Sources (Zero Mock Policy)

Strata Ops integrates **four live external data sources**. Every query retrieves real-world, unmocked data:

| Source | Integration Endpoint | Telemetry Extracted & Operational Value |
|---|---|---|
| **1. FAA Command Center (NAS Status)** | `https://nasstatus.faa.gov/api/airport-status-information` | Live Ground Stops, Ground Delay Programs (GDP), Arrival/Departure Delays, and Airport Closures. Provides exact average delay minutes, maximum hold times, and root cause reason codes (thunderstorms, low ceilings, wind, volume, construction). |
| **2. NOAA National Weather Service (NWS)** | `https://api.weather.gov/alerts/active?point={lat},{lon}` | Official real-time Weather Warnings, Watches, and Advisories (Tornado, Blizzard, Severe Thunderstorm, High Wind, Dense Fog, Coastal Flood) affecting terminal airspaces. |
| **3. NOAA Aviation Weather Center (AWC)** | `https://aviationweather.gov/api/data/metar` & `/taf` & `/airsigmet` | Real-time METAR surface observations: Flight Category (VFR, MVFR, IFR, LIFR), cloud ceilings, runway visual range, wind gusts, and barometric pressure. Plus 24–30 hour forward-looking TAF forecasts and airborne SIGMETs (convection, turbulence, icing). |
| **4. Open-Meteo Atmospheric Models** | `https://api.open-meteo.com/v1/forecast` | High-resolution numerical weather models (HRRR/GFS/ECMWF blend) providing hour-by-hour timelines of precipitation probability, weather codes, and surface wind gusts for departure, destination, and the mid-route corridor. |

---

## 3. Where AI Fits In: Multi-Tier Intelligence Architecture

The application avoids treating AI as a generic chatbot wrapper. Instead, AI is integrated at three distinct architectural layers:

```
[4 Live Telemetry Feeds]
 (FAA NAS + NOAA NWS + Aviation METAR/TAF + Open-Meteo)
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ Tier 1: Multi-Signal Bayesian Risk Fusion Engine        │
│ • Airspace & ATC Capacity Risk (0-100)                  │
│ • Terminal Meteorological Risk (0-100)                  │
│ • En-Route Corridor Turbulence Risk (0-100)             │
│ • Non-linear Catastrophic Bottleneck Booster            │
│ • Probabilistic Calibration: Delay %, Cancel %, Conn %  │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Tier 2: Disruption Synthesizer & Uncertainty Engine     │
│ • Traceable Evidence Dossier (Links claims to sensors)  │
│ • Operational Action Matrix (Traveler & Ops Team roles) │
│ • Uncertainty Quantification (Knowns vs Model Variance) │
│ • Sensitivity Tipping Points (Wind/fog thresholds)      │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Tier 3: LLM Cognitive Synthesis (Google Gemini 2.5)     │
│ • Generates executive operational memos                 │
│ • Counterfactual timing reasoning ("What if rebooked?") │
│ • Graceful zero-crash fallback to Built-in Engine       │
└─────────────────────────────────────────────────────────┘
```

### 1. Quantitative Risk Fusion & Probability Modeling
- Telemetry signals are normalized into component risk dimensions: Airspace Capacity, Departure Weather, Arrival Weather, and En-Route Corridor.
- A **non-linear threat booster** ensures that catastrophic single-point bottlenecks (such as an active FAA Ground Stop or a Blizzard Warning) appropriately elevate the composite score even if other dimensions are mild.
- Statistical probabilities are generated for:
  - **Delay Probability (%)** and expected delay range (`0-15m`, `20-45m`, `45-90m`, `90-180m+`).
  - **Cancellation Probability (%)**.
  - **Missed Connection Vulnerability (%)**.

### 2. Evidence Attribution & Traceability
Every single risk insight is traceable to its source. Users can click **"Inspect Raw Telemetry"** on any evidence card to review the exact FAA XML snippet, raw METAR code string, or NWS emergency bulletin.

### 3. Uncertainty & Sensitivity Quantification
Operations decisions require knowing *how sure* the system is:
- **Confirmed Ground Truth**: Factual measurements (e.g., active FAA Ground Delay Program with 51-min average delay, METAR measured IFR ceiling at 800 ft).
- **Model Forecast Variables**: Forward-looking atmospheric projections with temporal variance windows (+/- 2 hours for frontal passage).
- **Sensitivity Tipping Points**: Explicitly identifies environmental triggers that would flip the risk (e.g., crosswinds exceeding 20 kts forcing runway reconfiguration, or fog burning off 1 hour earlier).

### 4. Generative LLM Integration (Gemini 2.5 Flash / Aerospace AI Coordinator)
- **Where to get an API Key**: A free Google Gemini API key can be obtained in seconds with any Google account from **[Google AI Studio](https://aistudio.google.com/app/apikey)**.
- **Zero API Key Requirement for Telemetry**: All live external telemetry feeds (FAA NAS Status, NOAA Aviation Weather METAR/TAF, NWS Emergency Bulletins, Open-Meteo forecasts) are 100% public U.S. government and open meteorological services that **require NO API key or payment**.
- **Dual-Engine Flexibility**:
  - **With Gemini Key**: Provides generative cognitive briefings and executive counterfactual memos. Enter it via the **"AI Engine"** button in the top navigation bar or in `.env` as `GEMINI_API_KEY`.
  - **Without API Key**: The platform automatically falls back to its built-in **AeroGuard Bayesian Fusion Engine**, delivering calibrated probabilities, evidence dossiers, and operational directives with 100% reliability and zero crashes.

---

## 4. Key User Experience Capabilities

1. **Nationwide U.S. Airport & City Resolution (2,036+ Airports)**:
   - Exhaustive coverage of 2,036 U.S. commercial, regional, and municipal airports (e.g. `LBB` Lubbock Preston Smith, `DFW`, `JFK`, `SFO`, `DEN`, `ORD`).
   - Supports 8,825+ search aliases: IATA codes (`LBB`, `LAX`), ICAO codes (`KLBB`, `KDFW`), city and regional names (`"Lubbock, TX"`, `"Dallas"`, `"San Francisco"`, `"Bay Area"`), plus dynamic network geocoding fallback.
2. **Dedicated Roadway Dynamics & Highway Routing Preferences**:
   - In **Roadway / Driving Mode**, flight-specific dynamics (FAA Ground Stops, airport ATC delays, great-circle flight arcs) are suppressed in favor of dedicated highway operations:
     - **Interstate Corridors (Fastest)**: Uses major interstate freeways (e.g. `I-20 W`, `I-80 W`, `I-95 S`) for minimum transit duration.
     - **State Highways (Scenic / Non-Toll)**: Routes via state and U.S. highways (e.g. `TX-114 W / US-380 W`) to bypass tolls and high-density urban choke points.
     - **Weather-Resilient Bypass**: Routes via lower-elevation bypasses (e.g. `US-84 W`) to circumvent high-elevation mountain passes and winter snowstorm corridors.
   - **Tactical Waypoint Halts**: Geocoded milestone stops every 2–4 hours for driver fatigue mitigation, EV Fast Charging hubs, and rest plazas.
   - **Roadside Lodging Contingencies**: Vetted motels and business hotels along the drive with explicit operational triggers (e.g. *Execute booking if pass closure or road blizzard is active past 17:00*).
   - **Interactive Road Corridor Map**: Visualizes the actual highway polyline, origin/destination road nodes, halt pins (`HALT 1`, `HALT 2`, `HALT 3`), and stay pins (`LODGE`).
3. **Fast 1-Click Evaluation Presets**:
   - `JFK → SFO (Tomorrow)`: Coastal fog, transcontinental corridor, and terminal wind outlook.
   - `ORD → BOS (Today)`: Live FAA Ground Delay Program at Boston Logan due to runway construction.
   - `ATL → MIA (Tomorrow)`: Convective thunderstorm and subtropical shower tracking.
   - `DEN → SEA (Tomorrow)`: Mountain wave turbulence and Pacific Northwest marine layer.
4. **Hour-by-Hour Travel Day Trajectory**:
   - 24-hour timeline displaying temperature, precipitation probability, wind gusts, and disruption index for each hour—automatically highlighting the **Optimal Flight Window**.
5. **Dual-Role Operational Action Matrix**:
   - **For Traveler**: Departure rebooking windows, carry-on luggage strategy, airport buffer time, and Northeast corridor rail alternatives.
   - **For Operations Team**: Itinerary priority watch flags, minimum connection window enforcement, airline waiver monitoring, and duty of care lodging pre-authorizations.
6. **Print / Export Ops Briefing**:
   - One-click formatted corporate travel advisory ready for emailing or printing.

---

## 5. Quickstart & Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.11)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Option A: One-Command Startup (Recommended)
```bash
./run.sh
```
*The script checks your Python environment, verifies dependencies, and boots the server.*

### Option B: Manual Setup
```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Configure Gemini API Key
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here (or set via UI modal)

# 4. Start the application
python main.py
```

Open your browser to:
**http://localhost:8000**

Interactive Swagger API Documentation is available at:
**http://localhost:8000/docs**

---

## 6. Running the Automated Test Suite

Strata Ops includes a comprehensive unit and integration test suite:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_disruption_engine.py -v
```

The test suite validates:
- Airport and city alias resolution across 2,036+ U.S. airports (including Lubbock `LBB`).
- Great-circle distance, duration, and midpoint calculations.
- Live FAA XML parser handling of Ground Stops, GDPs, and closures.
- Aviation METAR parsing and flight category classification (VFR/MVFR/IFR/LIFR).
- NWS emergency alert severity scoring.
- Probabilistic Bayesian risk fusion boundary calculations.
- Uncertainty analysis and sensitivity quantification.
- Roadway service routing across Interstate, State Highway, and Weather-Resilient preferences with geocoded waypoints.
- Stay service generation of tactical halts, EV hubs, and roadside motel contingencies with spatial coordinates.

---

## 7. Project Structure

```
├── app/
│   ├── airports.py                   # 80+ US airports registry, city aliases, great-circle geometry
│   ├── main.py                       # FastAPI application, parallel orchestrator, REST routes
│   ├── models.py                     # Pydantic data schemas for requests, responses, evidence, actions
│   ├── services/
│   │   ├── faa_service.py            # Real-time FAA Command Center NAS XML integration
│   │   ├── aviation_weather_service.py # NOAA AWC METAR, TAF, and AIRSIGMET service
│   │   ├── nws_service.py            # NOAA National Weather Service active alerts service
│   │   └── forecast_service.py       # Open-Meteo numerical weather & hourly timeline service
│   └── ai/
│       ├── risk_fusion.py            # Multi-source Bayesian risk fusion engine
│       ├── synthesizer.py            # Evidence attribution, action matrices, uncertainty analysis
│       └── llm_client.py             # Google Gemini 2.5 Flash SDK integration
├── static/
│   ├── index.html                    # Responsive operations center dashboard UI
│   ├── app.js                        # Client-side reactivity, Leaflet map, telemetry toggles
│   └── style.css                     # Dark-mode styling, risk dials, print styles
├── tests/
│   └── test_disruption_engine.py     # Automated test suite
├── .env.example                      # Environment configuration template
├── requirements.txt                  # Dependency specifications
├── run.sh                            # One-command executable runner
├── main.py                           # Top-level server launcher
└── README.md                         # Comprehensive project documentation
```

---

## 8. What We Would Change Before Deploying to Production

While this prototype delivers a complete, unmocked end-to-end experience, deploying to enterprise production for 10,000+ business travelers would involve:

1. **Inbound Aircraft Tail-Number Tracking (ADS-B)**:
   - Integrate live flight tracking (e.g., FlightAware AeroAPI or OpenSky Network) to trace the *physical inbound aircraft* assigned to the employee's flight 2–3 legs prior, detecting rolling turnaround delays hours before airlines officially post them.
2. **Corporate Booking Tool / GDS Integration**:
   - Webhooks with corporate travel management systems (Concur, Navan, Amex GBT, Sabre) to ingest PNRs and employee traveler profiles automatically.
3. **Automated Notification Dispatch**:
   - Slack, Microsoft Teams, SMS, and WhatsApp bots that alert the traveling employee and their travel manager automatically when their trip's risk score crosses above 60.
4. **Machine Learning Model Trained on Historical DOT BTS Data**:
   - Train an XGBoost model on the Bureau of Transportation Statistics (BTS) 10-year database of U.S. domestic flights to calibrate airline-specific and route-specific delay propensities (e.g., specific carrier on-time performance at Newark vs JFK).
5. **Caching & Resiliency Layer**:
   - Implement Redis caching with stale-while-revalidate (e.g., 5-minute TTL on FAA status, 15-minute TTL on METARs) to ensure millisecond response times and resilience during external agency downtime.
