/**
 * Strata Ops // U.S. Corporate Travel Disruption Intelligence Client
 * Handles real-time API communication, Leaflet flight route visualization,
 * animated probability dials, interactive action matrix, and traceable evidence filtering.
 */

let flightMap = null;
let currentAssessment = null;
let activeEvidenceFilter = 'all';

// Real-Time Visual Overlays State
let tomtomApiKey = localStorage.getItem('strata_tomtom_api_key') || '';
let tomtomTrafficLayer = null;
let tomtomIncidentsLayer = null;
let nexradRadarLayer = null;
let isTomTomTrafficActive = false;
let isTomTomIncidentsActive = false;
let isNexradRadarActive = false;

function getIsoDate(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function syncDatePresetButtons(selectedDate) {
  const todayBtn = document.getElementById('datePresetTodayBtn');
  const tmrwBtn = document.getElementById('datePresetTomorrowBtn');
  if (!todayBtn || !tmrwBtn) return;

  const todayStr = getIsoDate(0);
  const tmrwStr = getIsoDate(1);

  if (selectedDate === todayStr) {
    todayBtn.className = 'text-[10px] px-2 py-0.5 rounded bg-blue-600 text-white font-semibold transition';
    tmrwBtn.className = 'text-[10px] px-2 py-0.5 rounded bg-surface-700 hover:bg-surface-600 text-gray-300 font-medium transition';
  } else if (selectedDate === tmrwStr) {
    tmrwBtn.className = 'text-[10px] px-2 py-0.5 rounded bg-blue-600 text-white font-semibold transition';
    todayBtn.className = 'text-[10px] px-2 py-0.5 rounded bg-surface-700 hover:bg-surface-600 text-gray-300 font-medium transition';
  } else {
    todayBtn.className = 'text-[10px] px-2 py-0.5 rounded bg-surface-700 hover:bg-surface-600 text-gray-300 font-medium transition';
    tmrwBtn.className = 'text-[10px] px-2 py-0.5 rounded bg-surface-700 hover:bg-surface-600 text-gray-300 font-medium transition';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  initSettings();
  initFormHandlers();
  initMap();
  initMapLayerToggles();

  const travelDateInput = document.getElementById('travelDateInput');
  const initialDate = travelDateInput?.value || getIsoDate(1);

  // Auto-trigger default query for instant demo on first load: JFK -> SFO tomorrow
  submitAssessment('JFK', 'SFO', initialDate, 'all_day');
});

/**
 * Settings & API Key handling (Gemini & TomTom Developer Keys)
 */
async function initSettings() {
  const settingsBtn = document.getElementById('settingsBtn');
  const settingsModal = document.getElementById('settingsModal');
  const closeSettingsBtn = document.getElementById('closeSettingsBtn');
  const saveKeyBtn = document.getElementById('saveKeyBtn');
  const clearKeyBtn = document.getElementById('clearKeyBtn');
  const keyInput = document.getElementById('geminiApiKeyInput');
  const tomtomInput = document.getElementById('tomtomApiKeyInput');
  const aiEngineLabel = document.getElementById('aiEngineLabel');
  const tomtomStatusIndicator = document.getElementById('tomtomStatusIndicator');

  // Load saved Gemini Key
  const savedGeminiKey = localStorage.getItem('strata_gemini_api_key') || '';
  if (savedGeminiKey && keyInput) {
    keyInput.value = savedGeminiKey;
    aiEngineLabel.textContent = 'Gemini 2.5 Active';
  }

  // Load saved TomTom Key
  const savedTomTomKey = localStorage.getItem('strata_tomtom_api_key') || '';
  if (savedTomTomKey) {
    tomtomApiKey = savedTomTomKey;
    if (tomtomInput) tomtomInput.value = savedTomTomKey;
  }

  // Auto-sync config from backend if configured in .env
  try {
    const cfgRes = await fetch('/api/config');
    if (cfgRes.ok) {
      const cfg = await cfgRes.json();
      if (cfg.tomtom_key && !tomtomApiKey) {
        tomtomApiKey = cfg.tomtom_key;
        if (tomtomInput) tomtomInput.value = tomtomApiKey;
      }
    }
  } catch (e) {
    // Non-fatal config fetch
  }

  updateTomTomUIStatus();

  if (settingsBtn) {
    settingsBtn.addEventListener('click', () => {
      settingsModal.classList.remove('hidden');
      lucide.createIcons();
    });
  }

  if (closeSettingsBtn) {
    closeSettingsBtn.addEventListener('click', () => {
      settingsModal.classList.add('hidden');
    });
  }

  if (saveKeyBtn) {
    saveKeyBtn.addEventListener('click', () => {
      // 1. Gemini Key
      const gVal = keyInput ? keyInput.value.trim() : '';
      if (gVal) {
        localStorage.setItem('strata_gemini_api_key', gVal);
        aiEngineLabel.textContent = 'Gemini 2.5 Active';
      } else {
        localStorage.removeItem('strata_gemini_api_key');
        aiEngineLabel.textContent = 'AI Engine';
      }

      // 2. TomTom Key
      const tVal = tomtomInput ? tomtomInput.value.trim() : '';
      if (tVal) {
        localStorage.setItem('strata_tomtom_api_key', tVal);
        tomtomApiKey = tVal;
      } else {
        localStorage.removeItem('strata_tomtom_api_key');
        tomtomApiKey = '';
      }

      updateTomTomUIStatus();
      applyBaseMapTiles();
      refreshActiveTomTomLayers();

      settingsModal.classList.add('hidden');
    });
  }

  if (clearKeyBtn) {
    clearKeyBtn.addEventListener('click', () => {
      if (keyInput) keyInput.value = '';
      if (tomtomInput) tomtomInput.value = '';
      localStorage.removeItem('strata_gemini_api_key');
      localStorage.removeItem('strata_tomtom_api_key');
      tomtomApiKey = '';
      aiEngineLabel.textContent = 'AI Engine';
      updateTomTomUIStatus();
      applyBaseMapTiles();
      refreshActiveTomTomLayers();
      settingsModal.classList.add('hidden');
    });
  }
}

function updateTomTomUIStatus() {
  const tomtomStatusIndicator = document.getElementById('tomtomStatusIndicator');
  if (!tomtomStatusIndicator) return;
  if (tomtomApiKey) {
    tomtomStatusIndicator.innerHTML = `<span class="text-emerald-400 font-semibold flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>TomTom Key Active</span>`;
  } else {
    tomtomStatusIndicator.innerHTML = `<span class="text-gray-500">TomTom: No Key</span>`;
  }
}

function refreshActiveTomTomLayers() {
  if (!flightMap) return;
  if (isTomTomTrafficActive) {
    if (tomtomTrafficLayer) flightMap.removeLayer(tomtomTrafficLayer);
    if (tomtomApiKey) {
      tomtomTrafficLayer = L.tileLayer(
        `https://api.tomtom.com/traffic/map/4/tile/flow/relative0/{z}/{x}/{y}.png?key=${tomtomApiKey}`,
        { maxZoom: 18, opacity: 0.85, zIndex: 15 }
      ).addTo(flightMap);
    } else {
      isTomTomTrafficActive = false;
      const dot = document.getElementById('tomtomTrafficDot');
      if (dot) dot.className = 'w-2 h-2 rounded-full bg-gray-500';
    }
  }

  if (isTomTomIncidentsActive) {
    if (tomtomIncidentsLayer) flightMap.removeLayer(tomtomIncidentsLayer);
    if (tomtomApiKey) {
      tomtomIncidentsLayer = L.tileLayer(
        `https://api.tomtom.com/traffic/map/4/tile/incidents/s0/{z}/{x}/{y}.png?key=${tomtomApiKey}`,
        { maxZoom: 18, opacity: 0.9, zIndex: 16 }
      ).addTo(flightMap);
    } else {
      isTomTomIncidentsActive = false;
      const dot = document.getElementById('tomtomIncidentsDot');
      if (dot) dot.className = 'w-2 h-2 rounded-full bg-gray-500';
    }
  }
}

/**
 * Interactive Visual Map Layer Toggles: TomTom Traffic, Incidents & NOAA Radar
 */
function initMapLayerToggles() {
  const trafficBtn = document.getElementById('toggleTomTomTrafficBtn');
  const incidentsBtn = document.getElementById('toggleTomTomIncidentsBtn');
  const radarBtn = document.getElementById('toggleNexradRadarBtn');
  const trafficDot = document.getElementById('tomtomTrafficDot');
  const incidentsDot = document.getElementById('tomtomIncidentsDot');
  const radarDot = document.getElementById('nexradRadarDot');
  const settingsModal = document.getElementById('settingsModal');

  // 1. Toggle TomTom Traffic Flow
  if (trafficBtn) {
    trafficBtn.addEventListener('click', () => {
      if (!tomtomApiKey) {
        // Prompt for key
        if (settingsModal) {
          settingsModal.classList.remove('hidden');
          const tInput = document.getElementById('tomtomApiKeyInput');
          if (tInput) tInput.focus();
        }
        return;
      }

      isTomTomTrafficActive = !isTomTomTrafficActive;
      if (isTomTomTrafficActive) {
        if (!tomtomTrafficLayer) {
          tomtomTrafficLayer = L.tileLayer(
            `https://api.tomtom.com/traffic/map/4/tile/flow/relative0/{z}/{x}/{y}.png?key=${tomtomApiKey}`,
            { maxZoom: 18, opacity: 0.85, zIndex: 15 }
          );
        }
        if (flightMap) tomtomTrafficLayer.addTo(flightMap);
        trafficDot.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-pulse';
      } else {
        if (flightMap && tomtomTrafficLayer) flightMap.removeLayer(tomtomTrafficLayer);
        trafficDot.className = 'w-2 h-2 rounded-full bg-gray-500';
      }
    });
  }

  // 2. Toggle TomTom Real-Time Incidents
  if (incidentsBtn) {
    incidentsBtn.addEventListener('click', () => {
      if (!tomtomApiKey) {
        if (settingsModal) {
          settingsModal.classList.remove('hidden');
          const tInput = document.getElementById('tomtomApiKeyInput');
          if (tInput) tInput.focus();
        }
        return;
      }

      isTomTomIncidentsActive = !isTomTomIncidentsActive;
      if (isTomTomIncidentsActive) {
        if (!tomtomIncidentsLayer) {
          tomtomIncidentsLayer = L.tileLayer(
            `https://api.tomtom.com/traffic/map/4/tile/incidents/s0/{z}/{x}/{y}.png?key=${tomtomApiKey}`,
            { maxZoom: 18, opacity: 0.9, zIndex: 16 }
          );
        }
        if (flightMap) tomtomIncidentsLayer.addTo(flightMap);
        incidentsDot.className = 'w-2 h-2 rounded-full bg-amber-400 animate-pulse';
      } else {
        if (flightMap && tomtomIncidentsLayer) flightMap.removeLayer(tomtomIncidentsLayer);
        incidentsDot.className = 'w-2 h-2 rounded-full bg-gray-500';
      }
    });
  }

  // 3. Toggle Free NOAA NEXRAD Weather Radar
  if (radarBtn) {
    radarBtn.addEventListener('click', () => {
      isNexradRadarActive = !isNexradRadarActive;
      if (isNexradRadarActive) {
        if (!nexradRadarLayer) {
          nexradRadarLayer = L.tileLayer.wms('https://mesonet.agron.iastate.edu/cgi-bin/wms/nexrad/n0r.cgi', {
            layers: 'nexrad-n0r-900913',
            format: 'image/png',
            transparent: true,
            opacity: 0.55,
            zIndex: 14,
          });
        }
        if (flightMap) nexradRadarLayer.addTo(flightMap);
        radarDot.className = 'w-2 h-2 rounded-full bg-blue-400 animate-pulse';
      } else {
        if (flightMap && nexradRadarLayer) flightMap.removeLayer(nexradRadarLayer);
        radarDot.className = 'w-2 h-2 rounded-full bg-gray-500';
      }
    });
  }
}


/**
 * Live Airport Autocomplete for Origin & Destination
 */
function setupAirportAutocomplete(inputId, suggestionsId) {
  const input = document.getElementById(inputId);
  const box = document.getElementById(suggestionsId);
  if (!input || !box) return;

  let debounceTimer = null;

  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const val = input.value.trim();
    if (val.length < 1) {
      box.classList.add('hidden');
      box.innerHTML = '';
      return;
    }

    debounceTimer = setTimeout(async () => {
      try {
        const resp = await fetch(`/api/airports?q=${encodeURIComponent(val)}`);
        if (!resp.ok) return;
        const data = await resp.json();
        const airports = data.airports || [];
        if (airports.length === 0) {
          box.classList.add('hidden');
          box.innerHTML = '';
          return;
        }

        box.innerHTML = '';
        airports.forEach(apt => {
          const item = document.createElement('button');
          item.type = 'button';
          item.className = 'w-full px-3 py-2 text-left hover:bg-surface-800 flex items-center justify-between group transition cursor-pointer text-xs';
          item.innerHTML = `
            <div class="truncate mr-2">
              <span class="font-mono font-bold text-white group-hover:text-blue-400">${apt.iata}</span>
              <span class="text-[11px] text-gray-300 ml-1.5 font-medium">${apt.city}${apt.state ? ', ' + apt.state : ''}</span>
              <div class="text-[10px] text-gray-400 truncate">${apt.name}</div>
            </div>
            <span class="text-[9px] font-mono text-gray-500 uppercase px-1.5 py-0.5 rounded bg-surface-800 border border-surface-700 flex-shrink-0">${apt.icao || ''}</span>
          `;
          item.addEventListener('click', (e) => {
            e.preventDefault();
            input.value = apt.iata;
            box.classList.add('hidden');
            box.innerHTML = '';
          });
          box.appendChild(item);
        });

        box.classList.remove('hidden');
      } catch (e) {
        // quiet error
      }
    }, 120);
  });

  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !box.contains(e.target)) {
      box.classList.add('hidden');
    }
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      box.classList.add('hidden');
    }
  });
}

/**
 * Form and Interactive Controls
 */
function initFormHandlers() {
  const form = document.getElementById('assessmentForm');
  const originInput = document.getElementById('originInput');
  const destInput = document.getElementById('destinationInput');
  const swapBtn = document.getElementById('swapAirportsBtn');
  const travelDateInput = document.getElementById('travelDateInput');
  const todayBtn = document.getElementById('datePresetTodayBtn');
  const tmrwBtn = document.getElementById('datePresetTomorrowBtn');
  const exportBtn = document.getElementById('exportBriefingBtn');

  // Swap airports
  swapBtn.addEventListener('click', () => {
    const tmp = originInput.value;
    originInput.value = destInput.value;
    destInput.value = tmp;
  });

  // Airport Autocomplete
  setupAirportAutocomplete('originInput', 'originSuggestions');
  setupAirportAutocomplete('destinationInput', 'destinationSuggestions');

  // Date input initialization and listener
  if (travelDateInput) {
    if (!travelDateInput.value) {
      travelDateInput.value = getIsoDate(1);
    }
    syncDatePresetButtons(travelDateInput.value);

    travelDateInput.addEventListener('change', () => {
      syncDatePresetButtons(travelDateInput.value);
    });
  }

  // Micro-preset buttons
  if (todayBtn) {
    todayBtn.addEventListener('click', () => {
      if (travelDateInput) {
        travelDateInput.value = getIsoDate(0);
        syncDatePresetButtons(travelDateInput.value);
      }
    });
  }

  if (tmrwBtn) {
    tmrwBtn.addEventListener('click', () => {
      if (travelDateInput) {
        travelDateInput.value = getIsoDate(1);
        syncDatePresetButtons(travelDateInput.value);
      }
    });
  }

  // Quick Chips
  document.querySelectorAll('.quick-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const code = btn.getAttribute('data-code');
      const el = document.getElementById(targetId);
      if (el) el.value = code;
    });
  });

  // Presets
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const orig = btn.getAttribute('data-orig');
      const dest = btn.getAttribute('data-dest');
      const dTag = btn.getAttribute('data-date');
      const targetDate = (dTag === 'today') ? getIsoDate(0) : getIsoDate(1);
      originInput.value = orig;
      destInput.value = dest;
      if (travelDateInput) {
        travelDateInput.value = targetDate;
        syncDatePresetButtons(targetDate);
      }
      submitAssessment(orig, dest, targetDate, 'all_day');
    });
  });

  // Tabs for Action Matrix
  const travelerTab = document.getElementById('travelerTabBtn');
  const opsTab = document.getElementById('opsTabBtn');
  const travelerList = document.getElementById('travelerActionsList');
  const opsList = document.getElementById('opsActionsList');

  // Corridor Mode tabs
  document.querySelectorAll('.mode-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.mode-tab-btn').forEach(b => {
        b.classList.remove('bg-blue-600', 'text-white');
        b.classList.add('text-gray-400');
      });
      btn.classList.add('bg-blue-600', 'text-white');
      btn.classList.remove('text-gray-400');
      const mode = btn.getAttribute('data-mode');
      document.getElementById('travelModeInput').value = mode;

      // Toggle Highway preference bar
      const hwContainer = document.getElementById('highwayPrefContainer');
      if (hwContainer) {
        if (mode === 'road' || mode === 'multimodal') {
          hwContainer.classList.remove('hidden');
        } else {
          hwContainer.classList.add('hidden');
        }
      }

      // Update Form Titles
      const formTitle = document.getElementById('formTitleText');
      const formSub = document.getElementById('formSubTitleText');
      if (formTitle && formSub) {
        if (mode === 'road') {
          formTitle.textContent = 'U.S. Interstate & State Highway Roadway Disruption Assessment';
          formSub.textContent = 'Query road surface weather hazards, black ice, mountain pass chain controls, and strategic waypoint halts.';
        } else if (mode === 'multimodal') {
          formTitle.textContent = 'U.S. Multimodal Air & Highway Corridor Assessment';
          formSub.textContent = 'Cross-analyze flight delays, airport ground stops, and roadway driving alternatives.';
        } else {
          formTitle.textContent = 'U.S. Flight Disruption Risk Assessment';
          formSub.textContent = 'Query real-time FAA airspace status, NOAA terminal meteorology, NWS advisories, and corridor atmospheric forecasts.';
        }
      }
      lucide.createIcons();
    });
  });

  // Highway Preference buttons
  document.querySelectorAll('.hw-pref-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.hw-pref-btn').forEach(b => {
        b.classList.remove('bg-emerald-600', 'text-white');
        b.classList.add('text-gray-400');
      });
      btn.classList.add('bg-emerald-600', 'text-white');
      btn.classList.remove('text-gray-400');
      const pref = btn.getAttribute('data-pref');
      const input = document.getElementById('highwayPrefInput');
      if (input) input.value = pref;
    });
  });

  travelerTab.addEventListener('click', () => {
    travelerTab.classList.add('bg-blue-600', 'text-white');
    travelerTab.classList.remove('text-gray-400');
    opsTab.classList.remove('bg-blue-600', 'text-white');
    opsTab.classList.add('text-gray-400');
    travelerList.classList.remove('hidden');
    opsList.classList.add('hidden');
  });

  opsTab.addEventListener('click', () => {
    opsTab.classList.add('bg-blue-600', 'text-white');
    opsTab.classList.remove('text-gray-400');
    travelerTab.classList.remove('bg-blue-600', 'text-white');
    travelerTab.classList.add('text-gray-400');
    opsList.classList.remove('hidden');
    travelerList.classList.add('hidden');
  });

  // Evidence Filters
  document.querySelectorAll('.ev-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.ev-filter-btn').forEach(b => {
        b.classList.remove('bg-blue-600', 'text-white');
        b.classList.add('bg-surface-700', 'text-gray-300');
      });
      btn.classList.add('bg-blue-600', 'text-white');
      btn.classList.remove('bg-surface-700', 'text-gray-300');
      activeEvidenceFilter = btn.getAttribute('data-filter');
      renderEvidence();
    });
  });

  // Export Briefing
  exportBtn.addEventListener('click', () => {
    window.print();
  });

  // Form Submit
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const orig = originInput.value.trim();
    const dest = destInput.value.trim();
    const d = travelDateInput ? travelDateInput.value : getIsoDate(1);
    const win = document.getElementById('timeWindowSelect').value;
    submitAssessment(orig, dest, d, win);
  });
}

/**
 * Execute Assessment Request to Backend
 */
async function submitAssessment(origin, destination, dateVal, timeWindow) {
  const loading = document.getElementById('loadingState');
  const results = document.getElementById('resultsContainer');
  const errorBox = document.getElementById('errorBox');
  const submitBtn = document.getElementById('submitBtn');
  const loadingStatusText = document.getElementById('loadingStatusText');
  const exportBtn = document.getElementById('exportBriefingBtn');

  errorBox.classList.add('hidden');
  loading.classList.remove('hidden');
  results.classList.add('hidden');
  submitBtn.disabled = true;

  const travelMode = document.getElementById('travelModeInput')?.value || 'air';
  const highwayPref = document.getElementById('highwayPrefInput')?.value || 'interstate';

  // Progressive loading status message (adapted to travel mode)
  const statusMessages = (travelMode === 'road') ? [
    'Scanning NWS Active Road Weather Watches, Warnings & Winter Advisories...',
    'Analyzing State DOT 511 Mountain Pass Chain Controls & Black Ice Sensors...',
    'Computing Interstate vs State Highway Corridor Routing Trajectories...',
    'Evaluating Tactical Halts (EV/Fuel Travel Plazas) & Motel Contingencies...',
    'Executing Multi-Source Roadway Risk Fusion & Synthesis...',
  ] : [
    'Querying FAA Command Center for Ground Stops & GDPs...',
    'Fetching NOAA Aviation Weather METARs & TAF forecasts...',
    'Scanning NWS Active Severe Weather Watches & Warnings...',
    'Running High-Resolution Corridor Atmospheric Forecasts...',
    'Executing Multi-Signal Bayesian Risk Fusion & LLM Synthesis...',
  ];
  let msgIdx = 0;
  const timer = setInterval(() => {
    msgIdx = (msgIdx + 1) % statusMessages.length;
    loadingStatusText.textContent = statusMessages[msgIdx];
  }, 900);

  const apiKey = localStorage.getItem('strata_gemini_api_key') || null;

  try {
    const resp = await fetch('/api/assess', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origin: origin,
        destination: destination,
        date: dateVal,
        time_window: timeWindow,
        travel_mode: travelMode,
        highway_preference: highwayPref,
        gemini_api_key: apiKey,
      }),
    });

    clearInterval(timer);

    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({ detail: 'Request failed.' }));
      throw new Error(errData.detail || 'Failed to complete disruption assessment.');
    }

    const data = await resp.json();
    currentAssessment = data;

    loading.classList.add('hidden');
    results.classList.remove('hidden');
    exportBtn.classList.remove('hidden');
    exportBtn.classList.add('flex');
    submitBtn.disabled = false;

    renderResults(data);

    if (flightMap) {
      setTimeout(() => {
        flightMap.invalidateSize();
        updateMap(data.route, data.travel_mode, data.halt_suggestions, data.stay_recommendations);
      }, 60);
    }
  } catch (err) {
    clearInterval(timer);
    loading.classList.add('hidden');
    submitBtn.disabled = false;
    errorBox.classList.remove('hidden');
    document.getElementById('errorMessage').textContent = err.message;
  }
}

/**
 * Populate Results in UI
 */
function renderResults(data) {
  // 1. Risk Score & Level
  const score = data.composite_risk_score;
  const level = data.risk_level;

  document.getElementById('riskScoreNumber').textContent = score;

  // Gauge Meter SVG animation
  const circle = document.getElementById('riskMeterCircle');
  const circumference = 251.2; // 2 * pi * 40
  const offset = circumference - (score / 100) * circumference;
  circle.style.strokeDashoffset = offset;

  // Gauge color based on level
  circle.classList.remove('text-emerald-500', 'text-amber-500', 'text-rose-500', 'text-red-600');
  const banner = document.getElementById('riskBanner');
  banner.classList.remove('risk-low', 'risk-moderate', 'risk-high', 'risk-critical');

  const badge = document.getElementById('riskLevelBadge');
  badge.classList.remove(
    'bg-emerald-500/20', 'text-emerald-400', 'border-emerald-500/30',
    'bg-amber-500/20', 'text-amber-400', 'border-amber-500/30',
    'bg-rose-500/20', 'text-rose-400', 'border-rose-500/30',
    'bg-red-500/30', 'text-red-300', 'border-red-500/50'
  );

  if (level === 'LOW') {
    circle.classList.add('text-emerald-500');
    banner.classList.add('risk-low');
    badge.classList.add('bg-emerald-500/20', 'text-emerald-400', 'border-emerald-500/30');
    badge.textContent = 'LOW DISRUPTION RISK';
  } else if (level === 'MODERATE') {
    circle.classList.add('text-amber-500');
    banner.classList.add('risk-moderate');
    badge.classList.add('bg-amber-500/20', 'text-amber-400', 'border-amber-500/30');
    badge.textContent = 'MODERATE DISRUPTION RISK';
  } else if (level === 'HIGH') {
    circle.classList.add('text-rose-500');
    banner.classList.add('risk-high');
    badge.classList.add('bg-rose-500/20', 'text-rose-400', 'border-rose-500/30');
    badge.textContent = 'HIGH DISRUPTION RISK';
  } else {
    circle.classList.add('text-red-600');
    banner.classList.add('risk-critical');
    badge.classList.add('bg-red-500/30', 'text-red-300', 'border-red-500/50');
    badge.textContent = 'CRITICAL DISRUPTION RISK';
  }

  // Route headline & verdict
  const isRoad = data.travel_mode === 'road';
  const isMultimodal = data.travel_mode === 'multimodal';

  if (isRoad) {
    document.getElementById('routeHeadlineBadge').textContent = `${data.route.origin.city} → ${data.route.destination.city} (DRIVE • ${data.route.travel_date.toUpperCase()})`;
    document.getElementById('delayProbTitle').textContent = 'Highway Delay Risk';
    document.getElementById('cancelProbTitle').textContent = 'Pass Closure Risk';
    document.getElementById('connRiskTitle').textContent = 'Fatigue / Slippage';

    document.getElementById('mapSectionTitle').textContent = 'Highway Corridor & Tactical Waypoints';
    document.getElementById('dimensionsSectionTitle').textContent = 'Roadway Risk Decomposition';
    document.getElementById('airspaceScoreLabel').textContent = 'Mountain Pass & Chain Controls';
    document.getElementById('arrWeatherScoreLabel').textContent = 'Destination Approach Road Surface';
    document.getElementById('depWeatherScoreLabel').textContent = 'Departure Beltway & Road Surface';
    document.getElementById('enrouteScoreLabel').textContent = 'Highway Corridor Crosswinds & Rain';

    const hway = (data.route.primary_interstates || [])[0] || 'Interstate Mainline';
    document.getElementById('routeFlightStats').textContent = `Drive: ${data.route.driving_distance_miles?.toLocaleString() || 'N/A'} mi • Est. ${data.route.driving_time_est || 'N/A'} • ${hway}`;
  } else {
    document.getElementById('routeHeadlineBadge').textContent = `${data.route.origin.iata} → ${data.route.destination.iata} (${isMultimodal ? 'MULTIMODAL' : 'AIR'} • ${data.route.travel_date.toUpperCase()})`;
    document.getElementById('delayProbTitle').textContent = 'Delay Risk';
    document.getElementById('cancelProbTitle').textContent = 'Cancellation';
    document.getElementById('connRiskTitle').textContent = 'Connection Risk';

    document.getElementById('mapSectionTitle').textContent = 'Airspace Corridor & Route Geometry';
    document.getElementById('dimensionsSectionTitle').textContent = 'Risk Decomposition by Dimension';
    document.getElementById('airspaceScoreLabel').textContent = 'FAA Airspace Programs & Capacity';
    document.getElementById('arrWeatherScoreLabel').textContent = 'Destination Terminal Conditions';
    document.getElementById('depWeatherScoreLabel').textContent = 'Departure Terminal Conditions';
    document.getElementById('enrouteScoreLabel').textContent = 'En-Route Turbulence & AIRSIGMETs';

    document.getElementById('routeFlightStats').textContent = `${data.route.distance_miles.toLocaleString()} mi • Est. ${data.route.flight_time_est}`;
  }

  document.getElementById('executiveVerdictText').textContent = data.executive_verdict;
  document.getElementById('headlineRiskSummary').textContent = data.headline_risk_summary;

  // 3 Probability Metrics
  document.getElementById('delayProbVal').textContent = `${data.delay_probability}%`;
  document.getElementById('delayRangeVal').textContent = data.expected_delay_range;
  document.getElementById('cancelProbVal').textContent = `${data.cancellation_probability}%`;
  document.getElementById('connRiskVal').textContent = `${data.missed_connection_risk}%`;

  // 4 Dimension Scores
  const dims = data.dimension_scores;
  setMeter('airspaceScoreVal', 'airspaceScoreBar', dims.airspace_atc);
  setMeter('arrWeatherScoreVal', 'arrWeatherScoreBar', dims.arrival_terminal);
  setMeter('depWeatherScoreVal', 'depWeatherScoreBar', dims.departure_terminal);
  setMeter('enrouteScoreVal', 'enrouteScoreBar', dims.enroute_corridor);

  // Map Update with halts and stays
  updateMap(data.route, data.travel_mode, data.halt_suggestions, data.stay_recommendations);

  // Hourly Timeline
  renderHourlyTimeline(data.hourly_timeline);

  // Actions
  renderActions(data.recommendations);

  // Uncertainty
  renderUncertainty(data.uncertainty);

  // AI Briefing
  document.getElementById('aiBriefingText').innerHTML = formatMarkdown(data.ai_briefing);
  document.getElementById('aiEngineBadge').textContent = data.engine_used;

  // Roadway Corridor, Halts & Stays
  renderRoadwayAndStays(data);

  // Evidence Dossier
  renderEvidence();

  lucide.createIcons();
}

function setMeter(textId, barId, score) {
  document.getElementById(textId).textContent = `${score} / 100`;
  const bar = document.getElementById(barId);
  bar.style.width = `${score}%`;
  bar.className = 'h-full rounded-full transition-all duration-700';
  if (score >= 70) {
    bar.classList.add('bg-rose-500');
  } else if (score >= 40) {
    bar.classList.add('bg-amber-500');
  } else {
    bar.classList.add('bg-emerald-500');
  }
}

/**
 * Leaflet Map Render
 */
let baseMapLayer = null;

function applyBaseMapTiles() {
  if (!flightMap) return;
  if (baseMapLayer) {
    flightMap.removeLayer(baseMapLayer);
    baseMapLayer = null;
  }

  if (tomtomApiKey) {
    // If TomTom developer API key is configured, use official TomTom Night tiles
    baseMapLayer = L.tileLayer(
      `https://api.tomtom.com/map/1/tile/basic/night/{z}/{x}/{y}.png?key=${tomtomApiKey}`,
      { maxZoom: 18, zIndex: 1 }
    ).addTo(flightMap);
  } else {
    // Zero-Key Native Dark Slate Canvas (ESRI Dark Gray - No Watermark, 100% Free)
    baseMapLayer = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      { maxZoom: 16, zIndex: 1, attribution: 'Tiles &copy; Esri' }
    ).addTo(flightMap);
  }
}

function initMap() {
  const mapEl = document.getElementById('mapContainer');
  if (!mapEl) return;
  flightMap = L.map('mapContainer', {
    zoomControl: false,
    attributionControl: false,
  }).setView([39.8283, -98.5795], 4);

  applyBaseMapTiles();
}

function updateMap(route, travelMode = 'air', halts = [], stays = []) {
  if (!flightMap) return;

  // Clear existing layers
  flightMap.eachLayer(layer => {
    if (layer instanceof L.Marker || layer instanceof L.Polyline) {
      flightMap.removeLayer(layer);
    }
  });

  const origLat = route.origin.lat;
  const origLon = route.origin.lon;
  const destLat = route.destination.lat;
  const destLon = route.destination.lon;
  const allCoords = [[origLat, origLon], [destLat, destLon]];

  if (travelMode === 'road') {
    // 1. Build Highway Corridor Polyline from highway_waypoints
    let waypoints = [];
    if (route.highway_waypoints && route.highway_waypoints.length > 0) {
      waypoints = route.highway_waypoints.map(wp => [wp.lat, wp.lon]);
    } else {
      waypoints = [[origLat, origLon], [destLat, destLon]];
    }

    waypoints.forEach(pt => allCoords.push(pt));

    // Draw Highway Polyline
    L.polyline(waypoints, {
      color: '#10b981',
      weight: 4,
      opacity: 0.9,
    }).addTo(flightMap);

    // Origin Road Marker
    const origIcon = L.divIcon({
      className: 'road-pin origin',
      html: `<span>START: ${route.origin.iata}</span>`,
      iconSize: [80, 24],
      iconAnchor: [40, 12],
    });
    L.marker([origLat, origLon], { icon: origIcon })
      .bindTooltip(`<b>Origin: ${route.origin.name}</b><br><span class="text-xs text-gray-400">Departure Corridor</span>`, { direction: 'top' })
      .addTo(flightMap);

    // Destination Road Marker
    const destIcon = L.divIcon({
      className: 'road-pin dest',
      html: `<span>END: ${route.destination.iata}</span>`,
      iconSize: [80, 24],
      iconAnchor: [40, 12],
    });
    L.marker([destLat, destLon], { icon: destIcon })
      .bindTooltip(`<b>Destination: ${route.destination.name}</b><br><span class="text-xs text-gray-400">Arrival Corridor</span>`, { direction: 'top' })
      .addTo(flightMap);

    // Render Intermediate Milestone Halts
    if (halts && halts.length > 0) {
      halts.forEach((halt, idx) => {
        if (halt.lat && halt.lon) {
          allCoords.push([halt.lat, halt.lon]);
          const haltIcon = L.divIcon({
            className: 'road-pin halt',
            html: `<span>HALT ${idx + 1}</span>`,
            iconSize: [64, 22],
            iconAnchor: [32, 11],
          });
          const haltTitle = halt.location_name || halt.name || `Waypoint Halt ${idx + 1}`;
          const haltTime = halt.estimated_drive_time || halt.recommended_stop_after || '2-3 hrs';
          const haltDist = halt.distance_from_origin_miles ? `${halt.distance_from_origin_miles} mi` : (halt.est_distance_from_origin || '');
          const haltReason = halt.rationale || halt.primary_reason || 'Fuel / EV recharge & rest';
          const facs = (halt.facilities || []).slice(0, 3).join(', ');
          L.marker([halt.lat, halt.lon], { icon: haltIcon })
            .bindTooltip(`<b>${haltTitle}</b><br><span class="text-xs text-blue-300">Stop at ~${haltTime} (${haltDist})</span><br><span class="text-xs text-gray-300">${haltReason}</span><br><span class="text-xs text-gray-400">Facilities: ${facs}</span>`, { direction: 'top' })
            .addTo(flightMap);
        }
      });
    }

    // Render Overnight Stay / Lodging Contingencies
    if (stays && stays.length > 0) {
      stays.forEach(stay => {
        if (stay.lat && stay.lon) {
          allCoords.push([stay.lat, stay.lon]);
          const stayIcon = L.divIcon({
            className: 'road-pin stay',
            html: `<span>LODGE</span>`,
            iconSize: [58, 22],
            iconAnchor: [29, 11],
          });
          const stayLoc = stay.location || stay.city_state || 'Corridor Exit';
          const stayExit = stay.highway_exit || 'Exit';
          const stayRole = stay.strategic_role || stay.contingency_trigger || 'Rest Stop';
          L.marker([stay.lat, stay.lon], { icon: stayIcon })
            .bindTooltip(`<b>${stay.name}</b> (${(stay.tier || 'HOTEL').toUpperCase()})<br><span class="text-xs text-purple-300">${stayLoc} • ${stayExit}</span><br><span class="text-xs text-amber-300">Contingency: ${stayRole}</span>`, { direction: 'top' })
            .addTo(flightMap);
        }
      });
    }

    // Fit bounds with comfortable padding
    const bounds = L.latLngBounds(allCoords);
    flightMap.fitBounds(bounds, { padding: [50, 50] });

  } else {
    // Airway Flight Arc Mode
    const midLat = route.midpoint.lat;
    const midLon = route.midpoint.lon;

    // Generate curved great-circle arc points
    const points = [];
    const numSteps = 40;
    for (let i = 0; i <= numSteps; i++) {
      const f = i / numSteps;
      const lat = origLat + (destLat - origLat) * f + Math.sin(Math.PI * f) * 3.5;
      const lon = origLon + (destLon - origLon) * f;
      points.push([lat, lon]);
    }

    // Draw Route Polyline
    L.polyline(points, {
      color: '#3b82f6',
      weight: 3,
      dashArray: '6, 6',
      opacity: 0.85,
    }).addTo(flightMap);

    // Markers
    const origIcon = L.divIcon({
      className: 'airport-pin origin',
      html: `<span>${route.origin.iata}</span>`,
      iconSize: [42, 22],
      iconAnchor: [21, 11],
    });

    const destIcon = L.divIcon({
      className: 'airport-pin dest-mod',
      html: `<span>${route.destination.iata}</span>`,
      iconSize: [42, 22],
      iconAnchor: [21, 11],
    });

    const midIcon = L.divIcon({
      className: 'airport-pin',
      html: `<span>MID</span>`,
      iconSize: [36, 18],
      iconAnchor: [18, 9],
    });

    L.marker([origLat, origLon], { icon: origIcon })
      .bindTooltip(`<b>${route.origin.iata}</b>: ${route.origin.name}`, { direction: 'top' })
      .addTo(flightMap);

    L.marker([destLat, destLon], { icon: destIcon })
      .bindTooltip(`<b>${route.destination.iata}</b>: ${route.destination.name}`, { direction: 'top' })
      .addTo(flightMap);

    L.marker([midLat, midLon], { icon: midIcon })
      .bindTooltip(`En-Route Airspace Corridor`, { direction: 'top' })
      .addTo(flightMap);

    // Fit bounds with padding
    const bounds = L.latLngBounds([
      [origLat, origLon],
      [destLat, destLon],
    ]);
    flightMap.fitBounds(bounds, { padding: [40, 40] });
  }
}

/**
 * Hourly Timeline Render
 */
function renderHourlyTimeline(timeline) {
  const container = document.getElementById('hourlyTimelineScroll');
  container.innerHTML = '';

  if (!timeline || timeline.length === 0) {
    container.innerHTML = '<div class="text-xs text-gray-500 py-2">Hourly model timeline unavailable.</div>';
    return;
  }

  // Find lowest disruption hour
  let minScore = 999;
  let bestHour = 'Morning';
  timeline.forEach(h => {
    const s = h.risk_level === 'critical' ? 90 : h.risk_level === 'high' ? 70 : h.risk_level === 'medium' ? 45 : 15;
    if (s < minScore) {
      minScore = s;
      bestHour = h.hour_label;
    }
  });
  document.getElementById('bestWindowBadge').textContent = `Optimal Flight Window: ~${bestHour}`;

  timeline.forEach(item => {
    const card = document.createElement('div');
    card.className = 'flex-shrink-0 w-24 bg-surface-900/90 rounded-xl p-2.5 border border-surface-700/70 text-center flex flex-col justify-between';

    let badgeClass = 'text-emerald-400 bg-emerald-500/10';
    if (item.risk_level === 'high' || item.risk_level === 'critical') {
      badgeClass = 'text-rose-400 bg-rose-500/10 border-rose-500/30';
    } else if (item.risk_level === 'medium') {
      badgeClass = 'text-amber-400 bg-amber-500/10 border-amber-500/30';
    }

    card.innerHTML = `
      <div class="text-[11px] font-mono text-gray-400">${item.hour_label}</div>
      <div class="my-1.5">
        <div class="text-xs font-bold text-white">${item.temp_f}°F</div>
        <div class="text-[10px] text-gray-400 truncate" title="${item.weather_desc}">${item.weather_desc}</div>
      </div>
      <div class="text-[10px] space-y-1 pt-1 border-t border-surface-700/50">
        <div class="flex items-center justify-between text-gray-400">
          <span>Precip</span>
          <span class="text-blue-300 font-mono font-medium">${item.precip_prob}%</span>
        </div>
        <div class="flex items-center justify-between text-gray-400">
          <span>Gusts</span>
          <span class="text-gray-200 font-mono font-medium">${item.wind_gusts_mph} mph</span>
        </div>
      </div>
      <div class="mt-2 text-[9px] uppercase font-bold px-1 py-0.5 rounded border ${badgeClass}">
        ${item.risk_level}
      </div>
    `;
    container.appendChild(card);
  });
}

/**
 * Operational Actions Render
 */
function renderActions(actions) {
  const travelerList = document.getElementById('travelerActionsList');
  const opsList = document.getElementById('opsActionsList');
  travelerList.innerHTML = '';
  opsList.innerHTML = '';

  actions.forEach(rec => {
    const el = document.createElement('div');
    el.className = 'p-3 rounded-xl bg-surface-900/80 border border-surface-700/80 space-y-1';

    let priorityBadge = '<span class="text-[10px] bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded font-semibold uppercase">Recommended</span>';
    if (rec.priority === 'high') {
      priorityBadge = '<span class="text-[10px] bg-rose-500/20 text-rose-400 px-2 py-0.5 rounded font-semibold uppercase">High Priority</span>';
    }

    el.innerHTML = `
      <div class="flex items-center justify-between">
        <h4 class="text-xs font-bold text-white">${rec.title}</h4>
        ${priorityBadge}
      </div>
      <p class="text-xs text-blue-300 font-medium">${rec.action}</p>
      <p class="text-[11px] text-gray-400 leading-relaxed">${rec.rationale}</p>
    `;

    if (rec.target === 'traveler') {
      travelerList.appendChild(el);
    } else {
      opsList.appendChild(el);
    }
  });

  if (travelerList.children.length === 0) {
    travelerList.innerHTML = '<div class="text-xs text-gray-400 p-2">Standard travel protocols apply.</div>';
  }
  if (opsList.children.length === 0) {
    opsList.innerHTML = '<div class="text-xs text-gray-400 p-2">Standard monitoring protocols apply.</div>';
  }
}

/**
 * Uncertainty Panel Render
 */
function renderUncertainty(unc) {
  document.getElementById('confidenceScoreVal').textContent = `${unc.confidence_score}%`;

  const confList = document.getElementById('confirmedFactorsList');
  const varList = document.getElementById('forecastVariablesList');
  const sensList = document.getElementById('sensitivityDriversList');

  confList.innerHTML = unc.confirmed_factors.map(f => `<li>${f}</li>`).join('') || '<li>None reported</li>';
  varList.innerHTML = unc.forecast_variables.map(v => `<li>${v}</li>`).join('') || '<li>Standard variance</li>';
  sensList.innerHTML = unc.sensitivity_drivers.map(s => `<li>${s}</li>`).join('') || '<li>Standard parameters</li>';
}

/**
 * Evidence Dossier Render with Collapsible Telemetry
 */
function renderEvidence() {
  const container = document.getElementById('evidenceList');
  container.innerHTML = '';

  if (!currentAssessment || !currentAssessment.evidence) return;

  const items = currentAssessment.evidence.filter(e => {
    if (activeEvidenceFilter === 'all') return true;
    return e.category === activeEvidenceFilter;
  });

  if (items.length === 0) {
    container.innerHTML = '<div class="col-span-2 text-xs text-gray-500 py-6 text-center">No telemetry items in this category.</div>';
    return;
  }

  items.forEach((item, idx) => {
    const card = document.createElement('div');
    card.className = 'bg-surface-900/90 rounded-xl border border-surface-700/80 p-3.5 space-y-2 flex flex-col justify-between';

    let sevBadge = 'text-gray-300 bg-surface-700';
    if (item.severity === 'critical') sevBadge = 'text-rose-400 bg-rose-500/20 border border-rose-500/30';
    else if (item.severity === 'high') sevBadge = 'text-amber-400 bg-amber-500/20 border border-amber-500/30';
    else if (item.severity === 'medium') sevBadge = 'text-blue-400 bg-blue-500/20 border border-blue-500/30';

    const rawId = `raw-telemetry-${idx}`;

    card.innerHTML = `
      <div>
        <div class="flex items-center justify-between text-[11px] mb-1">
          <span class="font-semibold text-blue-400 font-mono">${item.source}</span>
          <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded ${sevBadge}">${item.severity}</span>
        </div>
        <h4 class="text-xs font-bold text-white">${item.title}</h4>
        <p class="text-xs text-gray-300 mt-1 leading-relaxed">${item.detail}</p>
      </div>

      ${item.raw_data ? `
        <div class="pt-2 border-t border-surface-700/50">
          <button class="text-[11px] text-gray-400 hover:text-white flex items-center gap-1 font-mono toggle-raw-btn" data-target="${rawId}">
            <span>Inspect Raw Telemetry</span>
            <span class="text-gray-500 text-[10px]">&darr;</span>
          </button>
          <pre id="${rawId}" class="hidden mt-1.5 p-2 bg-black/60 rounded border border-surface-700 text-[10px] text-emerald-400 font-mono whitespace-pre-wrap overflow-x-auto max-h-36">${escapeHtml(item.raw_data)}</pre>
        </div>
      ` : ''}
    `;

    container.appendChild(card);
  });

  // Toggle raw pre
  container.querySelectorAll('.toggle-raw-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const el = document.getElementById(targetId);
      el.classList.toggle('hidden');
    });
  });
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/**
 * Basic Markdown to HTML formatter for Briefing
 */
function formatMarkdown(md) {
  if (!md) return '';
  let html = md
    .replace(/^### (.*$)/gim, '<h3 class="text-sm font-bold text-white uppercase tracking-wider mt-3 mb-1">$1</h3>')
    .replace(/^## (.*$)/gim, '<h2 class="text-base font-bold text-white mt-4 mb-2">$1</h2>')
    .replace(/^\*\*([^*]+)\*\*/gim, '<strong class="text-white">$1</strong>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong class="text-white">$1</strong>')
    .replace(/^- (.*$)/gim, '<li class="ml-4 list-disc text-gray-300 my-0.5">$1</li>')
    .replace(/\n\n/g, '<div class="h-2"></div>')
    .replace(/\n/g, '<br>');
  return html;
}

/**
 * Render Interstate Roadway Hazards, Waypoint Halts, and Stay/Motel Contingencies
 */
function renderRoadwayAndStays(data) {
  const badge = document.getElementById('roadwayStatsBadge');
  const route = data.route;
  const interstates = (route.primary_interstates || []).join(' / ');
  badge.innerHTML = `<span class="text-emerald-400 font-semibold uppercase tracking-wider text-[11px] mr-1">Corridor:</span><strong>${route.driving_distance_miles?.toLocaleString() || 'N/A'} mi</strong> <span class="text-gray-400 font-normal">(~${route.driving_time_est || 'N/A'})</span> &bull; <span class="text-blue-300 font-mono">${interstates}</span>`;

  // 1. Roadway Disruptions
  const dispList = document.getElementById('roadwayDisruptionsList');
  dispList.innerHTML = '';
  const roadDisruptions = data.roadway_disruptions || [];
  if (roadDisruptions.length === 0) {
    dispList.innerHTML = '<div class="col-span-2 text-xs text-gray-400 p-2">Standard highway conditions. No road weather advisories.</div>';
  } else {
    roadDisruptions.forEach(rd => {
      const el = document.createElement('div');
      let badgeColor = 'text-blue-400 bg-blue-500/10 border-blue-500/30';
      if (rd.severity === 'critical' || rd.severity === 'high') {
        badgeColor = 'text-rose-400 bg-rose-500/10 border-rose-500/30';
      } else if (rd.severity === 'medium') {
        badgeColor = 'text-amber-400 bg-amber-500/10 border-amber-500/30';
      }
      el.className = 'p-3 bg-surface-900/90 rounded-xl border border-surface-700/80 space-y-1';
      el.innerHTML = `
        <div class="flex items-center justify-between text-[11px]">
          <span class="font-bold text-white font-mono">${rd.highway}</span>
          <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${badgeColor}">${rd.condition_type}</span>
        </div>
        <div class="text-xs text-amber-300 font-medium">${rd.segment}</div>
        <p class="text-[11px] text-gray-300 leading-relaxed">${rd.description}</p>
        <div class="text-[10px] text-gray-500 pt-1 flex justify-between">
          <span>Est. Highway Delay: +${rd.delay_estimate_minutes}m</span>
          <span>Source: ${rd.source}</span>
        </div>
      `;
      dispList.appendChild(el);
    });
  }

  // 2. Halts along the way
  const haltList = document.getElementById('haltSuggestionsList');
  haltList.innerHTML = '';
  const halts = data.halt_suggestions || [];
  halts.forEach(h => {
    const el = document.createElement('div');
    el.className = 'p-3 bg-surface-900/80 rounded-xl border border-surface-700/70 space-y-1';
    el.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="text-xs font-bold text-white flex items-center gap-1.5">
          <span class="w-4 h-4 rounded-full bg-blue-500/20 text-blue-400 text-[10px] flex items-center justify-center font-mono font-bold">${h.stop_number}</span>
          <span>${h.location_name}</span>
        </span>
        <span class="text-[10px] font-mono text-gray-400">${h.estimated_drive_time} (${h.distance_from_origin_miles} mi)</span>
      </div>
      <p class="text-[11px] text-blue-300 font-medium">${h.rationale}</p>
      <div class="flex flex-wrap gap-1 pt-1">
        ${(h.facilities || []).map(f => `<span class="text-[9px] bg-surface-700 text-gray-300 px-1.5 py-0.5 rounded">${f}</span>`).join('')}
      </div>
    `;
    haltList.appendChild(el);
  });

  // 3. Stay / Motel Recommendations
  const stayList = document.getElementById('stayRecommendationsList');
  stayList.innerHTML = '';
  const stays = data.stay_recommendations || [];
  stays.forEach(s => {
    const el = document.createElement('div');
    el.className = 'p-3 bg-surface-900/80 rounded-xl border border-surface-700/70 space-y-1.5';
    let tierBadge = 'bg-blue-500/20 text-blue-300 border-blue-500/30';
    if (s.tier === 'emergency_shelter') tierBadge = 'bg-rose-500/20 text-rose-300 border-rose-500/30';
    else if (s.tier === 'budget_motel') tierBadge = 'bg-amber-500/20 text-amber-300 border-amber-500/30';

    el.innerHTML = `
      <div class="flex items-center justify-between">
        <div>
          <h5 class="text-xs font-bold text-white">${s.name}</h5>
          <span class="text-[10px] text-gray-400 font-mono">${s.location} (${s.highway_exit})</span>
        </div>
        <div class="text-right">
          <span class="text-[9px] uppercase font-bold px-1.5 py-0.5 rounded border ${tierBadge}">${s.tier.replace('_', ' ')}</span>
          <span class="text-[10px] font-mono text-gray-400 block">${s.price_tier}</span>
        </div>
      </div>
      <p class="text-[11px] text-gray-300 leading-relaxed">${s.strategic_role}</p>
      <div class="bg-surface-800/80 p-2 rounded-lg border border-surface-700/60 text-[10px] text-amber-300">
        <span class="text-gray-400 font-bold uppercase tracking-wider text-[9px] mr-1">Contingency Trigger:</span>${s.contingency_trigger}
      </div>
      <div class="flex flex-wrap gap-1 pt-0.5">
        ${(s.amenities || []).map(a => `<span class="text-[9px] bg-surface-700/60 text-gray-400 px-1.5 py-0.5 rounded">${a}</span>`).join('')}
      </div>
    `;
    stayList.appendChild(el);
  });
}

