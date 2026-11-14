// --------------------------------------------------
// MARSWARD MODULES
// Navigation, Survival Simulator and Science Explorer.
//
// This file does not import the map library, so these
// modules keep working if the map fails to load.
// script.js listens for the "marsward:view" event.
// --------------------------------------------------

const API_BASE = "";

function element(id) {
    return document.getElementById(id);
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
}

function formatNumber(value, decimals = 1) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) {
        return "N/A";
    }

    return Number(value).toLocaleString("en-US", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

async function fetchJson(url, options) {
    const response = await fetch(url, options);

    let data = null;

    try {
        data = await response.json();
    } catch (error) {
        data = null;
    }

    if (!response.ok) {
        throw new Error(
            (data && data.error) || `Request failed (${response.status})`
        );
    }

    return data;
}

// --------------------------------------------------
// NAVIGATION
// --------------------------------------------------

const VIEW_IDS = {
    map: "view-map",
    survival: "view-survival",
    science: "view-science"
};

const navItems = document.querySelectorAll(".nav-item[data-view]");

function showView(view, mode, navItem) {
    Object.entries(VIEW_IDS).forEach(([name, id]) => {
        const section = element(id);

        if (section) {
            section.hidden = name !== view;
        }
    });

    navItems.forEach(item => {
        item.classList.toggle("active", item === navItem);
    });

    if (view === "science") {
        loadScience();
    }

    window.dispatchEvent(
        new CustomEvent("marsward:view", {
            detail: { view, mode: mode || null }
        })
    );
}

navItems.forEach(item => {
    item.addEventListener("click", () => {
        showView(item.dataset.view, item.dataset.mode, item);
    });
});

// --------------------------------------------------
// SURVIVAL SIMULATOR
// --------------------------------------------------

const SURVIVAL_FIELDS = {
    crew: "sv-crew",
    duration: "sv-duration",
    water: "sv-water",
    food: "sv-food",
    oxygen: "sv-oxygen",
    reserve: "sv-reserve",
    supplyWater: "sv-supply-water",
    supplyFood: "sv-supply-food",
    supplyOxygen: "sv-supply-oxygen"
};

const STATUS_TEXT = {
    SUFFICIENT: "SUFFICIENT",
    RESERVE_AT_RISK: "RESERVE AT RISK",
    INSUFFICIENT: "INSUFFICIENT",
    NOT_ASSESSED: "NOT ASSESSED"
};

const STATUS_CLASS = {
    SUFFICIENT: "ok",
    RESERVE_AT_RISK: "warn",
    INSUFFICIENT: "critical",
    NOT_ASSESSED: "neutral"
};

let survivalDefaults = null;

function fieldValue(key) {
    const input = element(SURVIVAL_FIELDS[key]);

    if (!input || input.value.trim() === "") {
        return null;
    }

    const value = Number(input.value);

    return Number.isFinite(value) ? value : null;
}

function setField(key, value) {
    const input = element(SURVIVAL_FIELDS[key]);

    if (input) {
        input.value = value;
    }
}

function applySurvivalDefaults(defaults) {
    setField("crew", defaults.crew_size);
    setField("duration", defaults.duration_sols);
    setField("water", defaults.daily_per_person_kg.water);
    setField("food", defaults.daily_per_person_kg.food);
    setField("oxygen", defaults.daily_per_person_kg.oxygen);
    setField("reserve", defaults.reserve_percent);
    setField("supplyWater", defaults.supplies_kg.water);
    setField("supplyFood", defaults.supplies_kg.food);
    setField("supplyOxygen", defaults.supplies_kg.oxygen);
}

function readSurvivalInputs() {
    return {
        crew_size: fieldValue("crew"),
        duration_sols: fieldValue("duration"),
        daily_per_person_kg: {
            water: fieldValue("water"),
            food: fieldValue("food"),
            oxygen: fieldValue("oxygen")
        },
        reserve_percent: fieldValue("reserve"),
        supplies_kg: {
            water: fieldValue("supplyWater"),
            food: fieldValue("supplyFood"),
            oxygen: fieldValue("supplyOxygen")
        }
    };
}

function renderSurvivalMessage(message, isError = false) {
    const target = element("survival-results");

    if (target) {
        target.innerHTML = `
            <div class="module-card">
                <p class="module-placeholder ${isError ? "error" : ""}">
                    ${escapeHtml(message)}
                </p>
            </div>
        `;
    }
}

function renderResourceCard(resource) {
    const statusClass = STATUS_CLASS[resource.status] || "neutral";
    const assessed = resource.available_kg !== null;

    // Bar scale: the larger of supplies and total requirement.
    const scale = Math.max(
        resource.total_required_kg,
        assessed ? resource.available_kg : 0
    ) || 1;

    const fill = assessed
        ? (resource.available_kg / scale) * 100
        : 0;

    const missionMark = (resource.base_requirement_kg / scale) * 100;
    const reserveMark = (resource.total_required_kg / scale) * 100;

    const marginText = assessed
        ? `${resource.margin_kg >= 0 ? "+" : "−"}${formatNumber(Math.abs(resource.margin_kg))} kg`
        : "N/A";

    return `
        <div class="module-card resource-card ${statusClass}">
            <div class="resource-header">
                <strong>${escapeHtml(resource.label)}</strong>
                <span class="status-pill ${statusClass}">
                    ${STATUS_TEXT[resource.status] || resource.status}
                </span>
            </div>

            <div class="resource-bar" title="Supplies on board against requirement">
                <div class="resource-bar-fill ${statusClass}" style="width:${fill.toFixed(1)}%"></div>
                <span class="resource-bar-mark" style="left:${missionMark.toFixed(1)}%"></span>
                <span class="resource-bar-mark reserve" style="left:${Math.min(reserveMark, 100).toFixed(1)}%"></span>
            </div>

            <div class="resource-bar-key">
                <span><i class="mark"></i> Mission need</span>
                <span><i class="mark reserve"></i> Need + reserve</span>
            </div>

            <div class="stat-grid">
                <div class="stat"><small>CREW USE PER DAY</small><strong>${formatNumber(resource.daily_crew_kg)} kg</strong></div>
                <div class="stat"><small>MISSION NEED</small><strong>${formatNumber(resource.base_requirement_kg)} kg</strong></div>
                <div class="stat"><small>EMERGENCY RESERVE</small><strong>${formatNumber(resource.reserve_kg)} kg</strong></div>
                <div class="stat"><small>TOTAL REQUIRED</small><strong>${formatNumber(resource.total_required_kg)} kg</strong></div>
                <div class="stat"><small>ON BOARD</small><strong>${assessed ? formatNumber(resource.available_kg) + " kg" : "N/A"}</strong></div>
                <div class="stat"><small>MARGIN VS TOTAL</small><strong>${marginText}</strong></div>
                <div class="stat"><small>SUPPLY LASTS</small><strong>${assessed ? formatNumber(resource.sols_supported) + " sols" : "N/A"}</strong></div>
            </div>
        </div>
    `;
}

function renderSurvivalResults(data) {
    const target = element("survival-results");

    if (!target) {
        return;
    }

    const mission = data.mission;
    const overall = data.overall;
    const statusClass = STATUS_CLASS[overall.status] || "neutral";

    const limiting = overall.limiting_resource_label
        ? `<p>Limiting resource: <strong>${escapeHtml(overall.limiting_resource_label)}</strong>,
           lasting ${formatNumber(overall.sols_supported)} of
           ${formatNumber(mission.duration_sols, 0)} sols.</p>`
        : "";

    const warnings = data.warnings.length
        ? data.warnings.map(warning => `
            <li class="${warning.level === "critical" ? "critical" : "warn"}">
                ${escapeHtml(warning.message)}
            </li>
        `).join("")
        : `<li class="ok">No survival warnings for this mission plan.</li>`;

    const assumptions = data.assumptions
        .map(text => `<li>${escapeHtml(text)}</li>`)
        .join("");

    target.innerHTML = `
        <div class="module-card overall-card ${statusClass}">
            <div class="resource-header">
                <strong>MISSION SURVIVAL STATUS</strong>
                <span class="status-pill ${statusClass}">
                    ${STATUS_TEXT[overall.status] || overall.status}
                </span>
            </div>
            <p>${escapeHtml(overall.message)}</p>
            ${limiting}
            <div class="stat-grid">
                <div class="stat"><small>CREW</small><strong>${mission.crew_size}</strong></div>
                <div class="stat"><small>DURATION</small><strong>${formatNumber(mission.duration_sols, 0)} sols</strong></div>
                <div class="stat"><small>EARTH DAYS</small><strong>${formatNumber(mission.duration_earth_days)}</strong></div>
                <div class="stat"><small>PERSON-DAYS</small><strong>${formatNumber(mission.person_days)}</strong></div>
            </div>
        </div>

        <div class="module-card">
            <p class="section-label">SURVIVAL WARNINGS</p>
            <ul class="warning-list">${warnings}</ul>
        </div>

        ${Object.values(data.resources).map(renderResourceCard).join("")}

        <div class="module-card">
            <p class="section-label">MODEL ASSUMPTIONS</p>
            <ul class="assumption-list">${assumptions}</ul>
        </div>
    `;
}

async function runSurvivalSimulation() {
    const button = element("sv-run");

    if (button) {
        button.disabled = true;
    }

    try {
        const data = await fetchJson(
            `${API_BASE}/api/survival/simulate`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(readSurvivalInputs())
            }
        );

        renderSurvivalResults(data);

    } catch (error) {
        console.error("Survival simulation error:", error);
        renderSurvivalMessage(error.message, true);

    } finally {
        if (button) {
            button.disabled = false;
        }
    }
}

async function initSurvival() {
    const form = element("survival-form");

    if (!form) {
        return;
    }

    form.addEventListener("submit", event => {
        event.preventDefault();
        runSurvivalSimulation();
    });

    const resetButton = element("sv-reset");

    if (resetButton) {
        resetButton.addEventListener("click", () => {
            if (survivalDefaults) {
                applySurvivalDefaults(survivalDefaults);
                runSurvivalSimulation();
            }
        });
    }

    try {
        const data = await fetchJson(`${API_BASE}/api/survival/defaults`);

        survivalDefaults = data.defaults;

        applySurvivalDefaults(survivalDefaults);
        runSurvivalSimulation();

    } catch (error) {
        console.error("Survival defaults error:", error);

        renderSurvivalMessage(
            "Could not reach the survival simulator. Check the backend.",
            true
        );
    }
}

// --------------------------------------------------
// SCIENCE EXPLORER
// --------------------------------------------------

let scienceLoaded = false;
let scienceLoading = false;

function renderFactCard(section) {
    const rows = section.facts.map(fact => `
        <div class="fact-row">
            <span>${escapeHtml(fact.label)}</span>
            <strong>${escapeHtml(fact.value)}</strong>
        </div>
    `).join("");

    return `
        <div class="module-card">
            <p class="section-label">${escapeHtml(section.title.toUpperCase())}</p>
            ${rows}
        </div>
    `;
}

function renderStat(label, value) {
    return `<div class="stat"><small>${label}</small><strong>${value}</strong></div>`;
}

function renderTerrainCards(terrain) {
    const elevation = terrain.elevation;
    const slope = terrain.slope;
    const summary = terrain.hazards.summary;
    const region = terrain.region;

    const relief = elevation.maximum - elevation.minimum;

    const hazardRows = Object.entries(summary.categories).map(
        ([label, values]) => {
            const cssClass = label.toLowerCase().replace(/\s+/g, "-");

            return `
                <div class="hazard-row">
                    <span class="hazard-row-label">
                        <span class="legend-swatch ${cssClass}"></span>
                        ${escapeHtml(label)}
                    </span>
                    <div class="hazard-track">
                        <div class="hazard-fill ${cssClass}"
                             style="width:${Math.max(values.percentage, 0.4)}%"></div>
                    </div>
                    <span class="hazard-row-value">
                        ${formatNumber(values.percentage, 2)}%
                        <small>${formatNumber(values.count, 0)} px</small>
                    </span>
                </div>
            `;
        }
    ).join("");

    return `
        <div class="module-card">
            <p class="section-label">ELEVATION · JEZERO STUDY REGION</p>
            <div class="stat-grid">
                ${renderStat("MINIMUM", formatNumber(elevation.minimum, 0) + " m")}
                ${renderStat("MAXIMUM", formatNumber(elevation.maximum, 0) + " m")}
                ${renderStat("MEAN", formatNumber(elevation.mean, 1) + " m")}
                ${renderStat("MEDIAN", formatNumber(elevation.median, 0) + " m")}
                ${renderStat("TOTAL RELIEF", formatNumber(relief, 0) + " m")}
            </div>
        </div>

        <div class="module-card">
            <p class="section-label">SLOPE · JEZERO STUDY REGION</p>
            <div class="stat-grid">
                ${renderStat("MEAN", formatNumber(slope.mean, 2) + "°")}
                ${renderStat("MEDIAN", formatNumber(slope.median, 2) + "°")}
                ${renderStat("75TH PERCENTILE", formatNumber(slope.percentile_75, 2) + "°")}
                ${renderStat("90TH PERCENTILE", formatNumber(slope.percentile_90, 2) + "°")}
                ${renderStat("95TH PERCENTILE", formatNumber(slope.percentile_95, 2) + "°")}
                ${renderStat("MAXIMUM", formatNumber(slope.maximum, 2) + "°")}
            </div>
        </div>

        <div class="module-card wide">
            <p class="section-label">TERRAIN HAZARD DISTRIBUTION</p>
            ${hazardRows}
            <p class="module-footnote">
                Share of ${formatNumber(summary.valid_pixels, 0)} classified MOLA pixels
                (${region.raster_rows} × ${region.raster_columns} raster).
            </p>
        </div>
    `;
}

function renderConditionsCard(conditions) {
    const rows = conditions.facts.map(fact => `
        <div class="fact-row">
            <span>${escapeHtml(fact.label)}</span>
            <strong>${escapeHtml(fact.value)}</strong>
        </div>
    `).join("");

    return `
        <div class="module-card wide">
            <p class="section-label">${escapeHtml(conditions.title.toUpperCase())}</p>
            ${rows}
            <p class="module-footnote">
                Source: <a href="${escapeHtml(conditions.source_url)}" target="_blank" rel="noopener">${escapeHtml(conditions.source)}</a>.
                ${escapeHtml(conditions.note)}
            </p>
        </div>
    `;
}

function renderStopsCard(stops) {
    const rows = stops.map((stop, index) => {
        const terrain = stop.terrain
            ? `${formatNumber(stop.terrain.elevation_metres, 0)} m · ${formatNumber(stop.terrain.slope_degrees, 1)}° slope · ${escapeHtml(stop.terrain.hazard_class)}`
            : "Terrain reading unavailable";

        return `
            <div class="stop-row">
                <div class="stop-text">
                    <strong>${escapeHtml(stop.name)}</strong>
                    <p>${escapeHtml(stop.summary)}</p>
                    <p class="stop-science">${escapeHtml(stop.science)}</p>
                    <small>
                        ${formatNumber(stop.latitude, 4)}° N, ${formatNumber(stop.longitude, 4)}° E${stop.approximate ? " (approximate)" : ""}
                        · ${terrain}
                    </small>
                </div>
                <button type="button" class="secondary-button inline" data-stop-index="${index}">
                    Set as destination
                </button>
            </div>
        `;
    }).join("");

    return `
        <div class="module-card wide">
            <p class="section-label">SCIENCE STOPS</p>
            ${rows}
        </div>
    `;
}

function bindStopButtons(target, stops) {
    target.querySelectorAll("[data-stop-index]").forEach(button => {
        button.addEventListener("click", () => {
            const stop = stops[Number(button.dataset.stopIndex)];

            const routeNav = document.querySelector(
                '.nav-item[data-mode="route"]'
            );

            showView("map", "route", routeNav);

            window.dispatchEvent(
                new CustomEvent("marsward:set-destination", {
                    detail: stop
                })
            );
        });
    });
}

async function loadScience() {
    if (scienceLoaded || scienceLoading) {
        return;
    }

    const target = element("science-content");

    if (!target) {
        return;
    }

    scienceLoading = true;

    try {
        const data = await fetchJson(`${API_BASE}/api/science/overview`);

        const terrainCards = data.terrain
            ? renderTerrainCards(data.terrain)
            : `
                <div class="module-card wide">
                    <p class="section-label">TERRAIN STATISTICS</p>
                    <p class="module-placeholder error">
                        MOLA terrain statistics are unavailable:
                        ${escapeHtml(data.terrain_error || "unknown error")}
                    </p>
                </div>
            `;

        const notes = data.notes
            .map(text => `<li>${escapeHtml(text)}</li>`)
            .join("");

        target.innerHTML = `
            <div class="science-grid">
                ${renderFactCard(data.mars)}
                ${renderFactCard(data.jezero)}
                ${data.stops && data.stops.length ? renderStopsCard(data.stops) : ""}
                ${data.conditions ? renderConditionsCard(data.conditions) : ""}
                ${terrainCards}
                <div class="module-card wide">
                    ${renderFactCard(data.dataset)
                        .replace('<div class="module-card">', "")
                        .replace(/<\/div>\s*$/, "")}
                </div>
                <div class="module-card wide">
                    <p class="section-label">READING THIS DATA</p>
                    <ul class="assumption-list">${notes}</ul>
                </div>
            </div>
        `;

        bindStopButtons(target, data.stops || []);

        scienceLoaded = true;

    } catch (error) {
        console.error("Science overview error:", error);

        target.innerHTML = `
            <div class="module-card">
                <p class="module-placeholder error">
                    Could not load science data. Check the backend.
                </p>
            </div>
        `;

    } finally {
        scienceLoading = false;
    }
}

// --------------------------------------------------
// INITIALIZE
// --------------------------------------------------

initSurvival();