import Map from "https://esm.sh/ol@10.6.1/Map.js";
import View from "https://esm.sh/ol@10.6.1/View.js";
import TileLayer from "https://esm.sh/ol@10.6.1/layer/Tile.js";
import ImageLayer from "https://esm.sh/ol@10.6.1/layer/Image.js";
import XYZ from "https://esm.sh/ol@10.6.1/source/XYZ.js";
import ImageStatic from "https://esm.sh/ol@10.6.1/source/ImageStatic.js";
import TileGrid from "https://esm.sh/ol@10.6.1/tilegrid/TileGrid.js";
import Projection from "https://esm.sh/ol@10.6.1/proj/Projection.js";
import VectorLayer from "https://esm.sh/ol@10.6.1/layer/Vector.js";
import VectorSource from "https://esm.sh/ol@10.6.1/source/Vector.js";
import Feature from "https://esm.sh/ol@10.6.1/Feature.js";
import Point from "https://esm.sh/ol@10.6.1/geom/Point.js";
import LineString from "https://esm.sh/ol@10.6.1/geom/LineString.js";
import Style from "https://esm.sh/ol@10.6.1/style/Style.js";
import CircleStyle from "https://esm.sh/ol@10.6.1/style/Circle.js";
import Fill from "https://esm.sh/ol@10.6.1/style/Fill.js";
import Stroke from "https://esm.sh/ol@10.6.1/style/Stroke.js";
import Text from "https://esm.sh/ol@10.6.1/style/Text.js";
import RegularShape from "https://esm.sh/ol@10.6.1/style/RegularShape.js";

// --------------------------------------------------
// CONFIGURATION
// --------------------------------------------------

const JEZERO = [77.7, 18.4];

// Study region. These are fallbacks; the real values are
// loaded from /api/config below, so a different dataset or
// region needs no change in this file.
const JEZERO_BOUNDS = {
    west: 74,
    east: 81,
    south: 16,
    north: 21
};

let RASTER_SIZE = [448, 320];

const NASA_TILE_URL =
    "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg";

const API_BASE = "";

// Default trip: Perseverance landing site to the Three Forks
// sample depot, about 3 km apart.
const DEFAULT_START = [77.4508, 18.4447];
const DEFAULT_END = [77.4, 18.455];

const DEFAULT_ZOOM = 7;

try {
    const configResponse = await fetch(`${API_BASE}/api/config`);

    if (configResponse.ok) {
        const config = await configResponse.json();

        Object.assign(JEZERO_BOUNDS, config.region.bounds);

        RASTER_SIZE = [
            config.region.raster_columns,
            config.region.raster_rows
        ];

        const datasetTag = document.getElementById("dataset-tag");

        if (datasetTag && config.dataset.short_name) {
            datasetTag.textContent = config.dataset.short_name;
        }
    }
} catch (error) {
    console.warn("Could not load /api/config; using default region.", error);
}

function boundsText() {
    return `${JEZERO_BOUNDS.west}°–${JEZERO_BOUNDS.east}° E, ${JEZERO_BOUNDS.south}°–${JEZERO_BOUNDS.north}° N`;
}

// --------------------------------------------------
// HELPER FUNCTIONS
// --------------------------------------------------

function element(id) {
    return document.getElementById(id);
}

function updateText(id, value) {
    const target = element(id);

    if (target) {
        target.textContent = value;
    }
}

function formatNumber(value, decimals = 2) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) {
        return "N/A";
    }

    return Number(value).toFixed(decimals);
}

function isInsideJezero(lon, lat) {
    return (
        lon >= JEZERO_BOUNDS.west &&
        lon <= JEZERO_BOUNDS.east &&
        lat >= JEZERO_BOUNDS.south &&
        lat <= JEZERO_BOUNDS.north
    );
}

// --------------------------------------------------
// MARS PROJECTION
// --------------------------------------------------

const marsProjection = new Projection({
    code: "MARS:EQ",
    units: "degrees",
    extent: [-180, -90, 180, 90]
});

// --------------------------------------------------
// NASA MOLA BASE MAP
// --------------------------------------------------

const nasaTileGrid = new TileGrid({
    extent: [-180, -90, 180, 90],
    origin: [-180, 90],
    resolutions: Array.from(
        { length: 9 },
        (_, zoom) => 360 / (256 * Math.pow(2, zoom))
    ),
    tileSize: 256
});

const terrainSource = new XYZ({
    url: NASA_TILE_URL,
    projection: marsProjection,
    tileGrid: nasaTileGrid,
    wrapX: false,
    maxZoom: 8
});

const terrainLayer = new TileLayer({
    source: terrainSource,
    zIndex: 1
});

// --------------------------------------------------
// MOLA HAZARD OVERLAY
// --------------------------------------------------

const hazardSource = new ImageStatic({
    url: `${API_BASE}/api/terrain/hazard-overlay`,
    imageExtent: [
        JEZERO_BOUNDS.west,
        JEZERO_BOUNDS.south,
        JEZERO_BOUNDS.east,
        JEZERO_BOUNDS.north
    ],
    projection: marsProjection,
    imageSize: RASTER_SIZE
});

const hazardLayer = new ImageLayer({
    source: hazardSource,
    opacity: 1,
    visible: true,
    zIndex: 2
});

// --------------------------------------------------
// BLOCKED TERRAIN OVERLAY
// --------------------------------------------------

// Squares steeper than the route slope limit. The image is
// rebuilt whenever the limit changes.

function regionExtent() {
    return [
        JEZERO_BOUNDS.west,
        JEZERO_BOUNDS.south,
        JEZERO_BOUNDS.east,
        JEZERO_BOUNDS.north
    ];
}

function blockedSource(maxSlope) {
    return new ImageStatic({
        url: `${API_BASE}/api/terrain/blocked-overlay?max_slope=${encodeURIComponent(maxSlope)}`,
        imageExtent: regionExtent(),
        projection: marsProjection,
        imageSize: RASTER_SIZE,
        interpolate: false
    });
}

const blockedLayer = new ImageLayer({
    source: blockedSource(20),
    visible: false,
    zIndex: 2.5
});

// --------------------------------------------------
// ROUTE, SCIENCE STOP AND MARKER LAYERS
// --------------------------------------------------

const LABEL_FONT = "600 11px 'Chakra Petch', 'Segoe UI', Arial, sans-serif";

function labelText(text, color, offsetY) {
    return new Text({
        text,
        offsetY,
        font: LABEL_FONT,
        fill: new Fill({ color }),
        stroke: new Stroke({ color: "#04060b", width: 4 })
    });
}

const routeSource = new VectorSource();

const routeLayer = new VectorLayer({
    source: routeSource,
    zIndex: 3,
    style: (feature) => {
        const color = feature.get("color") || "#ff9f43";

        // Soft glow underneath, bright dashed core on top.
        return [
            new Style({
                stroke: new Stroke({ color: color + "40", width: 11 })
            }),
            new Style({
                stroke: new Stroke({ color: "#04060b", width: 5 })
            }),
            new Style({
                stroke: new Stroke({
                    color,
                    width: 3,
                    lineDash: [10, 6]
                })
            })
        ];
    }
});

// Named science stops (yellow diamonds). Click one to make it
// the destination.

const stopsSource = new VectorSource();

const stopsLayer = new VectorLayer({
    source: stopsSource,
    zIndex: 4,
    declutter: true,
    style: (feature) => new Style({
        image: new RegularShape({
            points: 4,
            radius: 7,
            fill: new Fill({ color: "#ffd23f" }),
            stroke: new Stroke({ color: "#04060b", width: 2 })
        }),
        text: labelText(feature.get("name"), "#ffd23f", 18)
    })
});

// Start (orange) and destination (blue) markers.

const POINT_STYLES = {
    start: { color: "#ff6a3d", label: "START" },
    end: { color: "#4de3ff", label: "DESTINATION" }
};

const markerSource = new VectorSource();

const markerLayer = new VectorLayer({
    source: markerSource,
    zIndex: 5,
    style: (feature) => {
        const config = POINT_STYLES[feature.get("role")] || POINT_STYLES.start;

        // Target-lock look: outer ring, solid core.
        return [
            new Style({
                image: new CircleStyle({
                    radius: 13,
                    stroke: new Stroke({
                        color: config.color,
                        width: 1.5,
                        lineDash: [4, 4]
                    })
                })
            }),
            new Style({
                image: new CircleStyle({
                    radius: 6,
                    fill: new Fill({ color: config.color }),
                    stroke: new Stroke({ color: "#ffffff", width: 2 })
                }),
                text: labelText(config.label, "#ffffff", -24)
            })
        ];
    }
});

// --------------------------------------------------
// MAP INITIALIZATION
// --------------------------------------------------

const map = new Map({
    target: "map",
    layers: [
        terrainLayer,
        hazardLayer,
        blockedLayer,
        routeLayer,
        stopsLayer,
        markerLayer
    ],
    view: new View({
        projection: marsProjection,
        center: JEZERO,
        zoom: DEFAULT_ZOOM,
        minZoom: 1,
        // Tiles stop at zoom 8; higher zooms enlarge them so
        // short trips of a few kilometres are still visible.
        maxZoom: 11,
        extent: [-180, -90, 180, 90]
    })
});

// --------------------------------------------------
// START AND DESTINATION POINTS
// --------------------------------------------------

const POINT_INPUTS = {
    start: ["start-lon", "start-lat"],
    end: ["end-lon", "end-lat"]
};

const pointFeatures = { start: null, end: null };

let clickMode = "start";

function drawPoint(role, lon, lat) {
    if (!pointFeatures[role]) {
        pointFeatures[role] = new Feature({
            geometry: new Point([lon, lat]),
            role
        });

        markerSource.addFeature(pointFeatures[role]);
    } else {
        pointFeatures[role].getGeometry().setCoordinates([lon, lat]);
    }
}

// Set the start or destination: updates the inputs and marker.
function setPoint(role, lon, lat) {
    const [lonId, latId] = POINT_INPUTS[role];

    element(lonId).value = Number(lon).toFixed(4);
    element(latId).value = Number(lat).toFixed(4);

    drawPoint(role, lon, lat);
}

function readPoint(role) {
    const [lonId, latId] = POINT_INPUTS[role];

    return [
        Number(element(lonId)?.value),
        Number(element(latId)?.value)
    ];
}

// Keep markers in step with typed coordinates.
Object.entries(POINT_INPUTS).forEach(([role, ids]) => {
    ids.forEach(id => {
        element(id)?.addEventListener("input", () => {
            const [lon, lat] = readPoint(role);

            if (Number.isFinite(lon) && Number.isFinite(lat)) {
                drawPoint(role, lon, lat);
            }
        });
    });
});

function setClickMode(mode) {
    clickMode = mode;

    element("click-start")?.classList.toggle("active", mode === "start");
    element("click-end")?.classList.toggle("active", mode === "end");
}

element("click-start")?.addEventListener("click", () => setClickMode("start"));
element("click-end")?.addEventListener("click", () => setClickMode("end"));

// --------------------------------------------------
// COORDINATE DISPLAY
// --------------------------------------------------

function updateCoordinates(lon, lat) {
    updateText("latitude", `${lat.toFixed(4)}°`);
    updateText("longitude", `${lon.toFixed(4)}°`);

    updateText(
        "map-coordinates",
        `LAT ${lat.toFixed(4)}° | LON ${lon.toFixed(4)}°`
    );
}

// --------------------------------------------------
// TERRAIN INSPECTION
// --------------------------------------------------

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
}

// Render label/value readings into one of the terrain cards.
function renderReadings(id, readings, note = "") {
    const target = element(id);

    if (!target) {
        return;
    }

    const rows = readings.map(([label, value]) => `
        <div class="terrain-reading">
            <small>${escapeHtml(label)}</small>
            <strong>${escapeHtml(value)}</strong>
        </div>
    `).join("");

    target.innerHTML = rows + (
        note
            ? `<span class="terrain-coordinate">${escapeHtml(note)}</span>`
            : ""
    );
}

function renderCardMessage(id, message) {
    const target = element(id);

    if (target) {
        target.innerHTML = `<p>${escapeHtml(message)}</p>`;
    }
}

async function inspectTerrain(lon, lat) {
    if (!isInsideJezero(lon, lat)) {
        renderCardMessage(
            "terrain-inspection",
            `Select a location inside the study area (${boundsText()}).`
        );

        return;
    }

    try {
        const response = await fetch(
            `${API_BASE}/api/terrain/inspect?lon=${encodeURIComponent(lon)}&lat=${encodeURIComponent(lat)}`
        );

        if (!response.ok) {
            throw new Error(`Terrain API returned ${response.status}`);
        }

        const data = await response.json();

        if (data.status !== "success") {
            throw new Error(data.message || "Terrain inspection failed.");
        }

        const terrain = data.terrain;
        const pixel = data.pixel_coordinates;
        const raster = data.raster_index;

        const note = pixel && raster
            ? `Pixel centre ${pixel.latitude.toFixed(4)}°, ${pixel.longitude.toFixed(4)}° · row ${raster.row}, column ${raster.column}`
            : "";

        renderReadings(
            "terrain-inspection",
            [
                ["ELEVATION", `${formatNumber(terrain.elevation_metres, 1)} m`],
                ["SLOPE", `${formatNumber(terrain.slope_degrees, 2)}°`],
                ["HAZARD CLASS", terrain.hazard_class || "Unknown"]
            ],
            note
        );

        console.log("MARSWARD terrain inspection:", data);

    } catch (error) {
        console.error("Terrain inspection error:", error);

        renderCardMessage(
            "terrain-inspection",
            "Could not retrieve terrain information. Check the backend."
        );
    }
}

// --------------------------------------------------
// SCIENCE STOPS
// --------------------------------------------------

async function loadScienceStops() {
    try {
        const response = await fetch(`${API_BASE}/api/science/stops`);

        if (!response.ok) {
            throw new Error(`Science stops returned ${response.status}`);
        }

        const data = await response.json();

        stopsSource.clear();

        data.stops.forEach(stop => {
            stopsSource.addFeature(
                new Feature({
                    geometry: new Point([stop.longitude, stop.latitude]),
                    name: stop.name,
                    stop
                })
            );
        });

    } catch (error) {
        console.error("Science stops error:", error);
    }
}

function useStopAsDestination(stop) {
    const lon = Number(stop.longitude);
    const lat = Number(stop.latitude);

    if (!Number.isFinite(lon) || !Number.isFinite(lat)) {
        return;
    }

    setPoint("end", lon, lat);
    updateCoordinates(lon, lat);
    inspectTerrain(lon, lat);

    updateText(
        "route-results",
        `Destination set to ${stop.name}. Calculate the route for a GO / NO-GO verdict.`
    );
}

// Sent by the Science Explorer view (modules.js).
window.addEventListener("marsward:set-destination", (event) => {
    if (event.detail) {
        useStopAsDestination(event.detail);
    }
});

// --------------------------------------------------
// MAP CLICK EVENT
// --------------------------------------------------

map.on("click", function (event) {
    // A click on a science stop makes it the destination.
    const stopFeature = map.forEachFeatureAtPixel(
        event.pixel,
        feature => feature,
        {
            layerFilter: layer => layer === stopsLayer,
            hitTolerance: 6
        }
    );

    if (stopFeature) {
        useStopAsDestination(stopFeature.get("stop"));
        return;
    }

    const [lon, lat] = event.coordinate;

    setPoint(clickMode, lon, lat);
    updateCoordinates(lon, lat);
    inspectTerrain(lon, lat);

    // After the start is placed, the next click sets the destination.
    if (clickMode === "start") {
        setClickMode("end");
    }
});

// --------------------------------------------------
// HAZARD OVERLAY TOGGLE
// --------------------------------------------------

const hazardToggle = element("hazard-toggle");
const hazardStatus = element("hazard-layer-status");

function updateHazardLayerVisibility(isVisible) {
    hazardLayer.setVisible(isVisible);
    hazardLayer.changed();
    map.render();

    if (hazardStatus) {
        hazardStatus.textContent = isVisible
            ? "OVERLAY: ON"
            : "OVERLAY: OFF";
    }

    console.log("Hazard overlay visibility:", isVisible);
}

if (hazardToggle) {
    hazardToggle.addEventListener("change", (event) => {
        updateHazardLayerVisibility(event.target.checked);
    });

    updateHazardLayerVisibility(hazardToggle.checked);
} else {
    console.warn("Hazard toggle element was not found.");
}

hazardSource.on("imageloadend", () => {
    console.log("MARSWARD: Hazard overlay image loaded successfully.");
});

hazardSource.on("imageloaderror", () => {
    console.error("MARSWARD: Hazard overlay image failed to load.");
});

// --------------------------------------------------
// HAZARD ANALYSIS (blocked terrain at the slope limit)
// --------------------------------------------------

const blockedToggle = element("blocked-toggle");
const hazardSlider = element("hazard-slope");

let blockedTimer = null;

function currentSlopeLimit() {
    const value = Number(element("eva-slope")?.value);

    return Number.isFinite(value) && value >= 1 && value <= 90 ? value : 20;
}

function setBlockedVisible(isVisible) {
    blockedLayer.setVisible(isVisible);

    if (blockedToggle) {
        blockedToggle.checked = isVisible;
    }

    updateText(
        "blocked-layer-status",
        isVisible ? "OVERLAY: ON" : "OVERLAY: OFF"
    );
}

async function refreshBlockedTerrain() {
    const limit = currentSlopeLimit();

    blockedLayer.setSource(blockedSource(limit));

    updateText("hazard-slope-value", `${limit}°`);

    if (hazardSlider && Number(hazardSlider.value) !== limit) {
        hazardSlider.value = Math.min(limit, Number(hazardSlider.max));
    }

    const stats = element("hazard-panel-stats");

    if (!stats) {
        return;
    }

    try {
        const response = await fetch(
            `${API_BASE}/api/terrain/blocked-summary?max_slope=${encodeURIComponent(limit)}`
        );

        if (!response.ok) {
            throw new Error(`Blocked summary returned ${response.status}`);
        }

        const data = await response.json();
        const categories = data.hazard_summary.categories;

        const classes = Object.entries(categories).map(([label, values]) => `
            <span class="route-stat">
                <span class="legend-swatch ${label.toLowerCase().replace(/\s+/g, "-")}"></span>
                ${escapeHtml(label)}: <strong>${formatNumber(values.percentage, 2)}%</strong>
            </span>
        `).join("");

        stats.innerHTML = `
            <div class="hazard-panel-headline">
                <span class="legend-swatch blocked"></span>
                <strong>${data.blocked_pixels.toLocaleString("en-US")}</strong>
                of ${data.total_pixels.toLocaleString("en-US")} squares are blocked
                (<strong>${formatNumber(data.blocked_percentage, 2)}%</strong>,
                about <strong>${Math.round(data.blocked_area_km2).toLocaleString("en-US")} km²</strong>)
                at a ${limit}° limit.
            </div>
            <div class="hazard-panel-classes">${classes}</div>
        `;

    } catch (error) {
        console.error("Blocked terrain error:", error);
        stats.textContent = "Could not load blocked terrain. Check the backend.";
    }
}

function scheduleBlockedRefresh() {
    clearTimeout(blockedTimer);
    blockedTimer = setTimeout(refreshBlockedTerrain, 200);
}

blockedToggle?.addEventListener("change", (event) => {
    setBlockedVisible(event.target.checked);
});

// The slider and the route planner's slope limit stay in step.
hazardSlider?.addEventListener("input", () => {
    if (element("eva-slope")) {
        element("eva-slope").value = hazardSlider.value;
    }

    updateText("hazard-slope-value", `${hazardSlider.value}°`);
    scheduleBlockedRefresh();
});

element("eva-slope")?.addEventListener("input", scheduleBlockedRefresh);

// Hazard Analysis shows its own panel in place of the route controls.
function setMapMode(mode) {
    const isHazard = mode === "hazard";

    const toggle = (id, hidden) => {
        const target = element(id);

        if (target) {
            target.hidden = hidden;
        }
    };

    toggle("hazard-panel", !isHazard);
    toggle("route-controls", isHazard);
    toggle("eva-controls", isHazard);
    toggle("route-results", isHazard);

    updateText(
        "map-title",
        isHazard ? "Hazard Analysis" : "Martian Surface Explorer"
    );

    updateText(
        "map-subtitle",
        isHazard
            ? "Slope classes and the terrain routes cannot cross"
            : "Explore NASA planetary terrain data"
    );

    if (isHazard) {
        if (hazardToggle && !hazardToggle.checked) {
            hazardToggle.checked = true;
            updateHazardLayerVisibility(true);
        }

        setBlockedVisible(true);
        refreshBlockedTerrain();
    }
}

// --------------------------------------------------
// TERRAIN SUMMARY
// --------------------------------------------------

async function loadTerrainSummary() {
    try {
        const response = await fetch(
            `${API_BASE}/api/terrain/summary`
        );

        if (!response.ok) {
            throw new Error(`Terrain summary returned ${response.status}`);
        }

        const data = await response.json();

        if (data.status !== "success") {
            throw new Error(data.message || "Could not load terrain summary.");
        }

        const elevation = data.elevation;
        const slope = data.slope;
        const categories = data.hazards.summary.categories;

        renderReadings(
            "terrain-statistics",
            [
                ["ELEVATION RANGE", `${formatNumber(elevation.minimum, 0)} m to ${formatNumber(elevation.maximum, 0)} m`],
                ["MEAN ELEVATION", `${formatNumber(elevation.mean, 1)} m`],
                ["MEAN SLOPE", `${formatNumber(slope.mean, 2)}°`],
                ["90TH PERCENTILE SLOPE", `${formatNumber(slope.percentile_90, 2)}°`],
                ["MAXIMUM SLOPE", `${formatNumber(slope.maximum, 2)}°`],
                ["GENTLE TERRAIN", `${formatNumber(categories.Gentle.percentage, 2)}%`],
                ["MODERATE TERRAIN", `${formatNumber(categories.Moderate.percentage, 2)}%`],
                ["STEEP TERRAIN", `${formatNumber(categories.Steep.percentage, 2)}%`],
                ["VERY STEEP TERRAIN", `${formatNumber(categories["Very Steep"].percentage, 2)}%`]
            ],
            "Full breakdown in Science Explorer."
        );

        updateText("terrain-status", "TERRAIN DATA LOADED");

        console.log("MARSWARD terrain summary:", data);

    } catch (error) {
        console.error("Terrain summary error:", error);

        renderCardMessage(
            "terrain-statistics",
            "Terrain statistics unavailable. Check the backend and the MOLA data file."
        );

        updateText("terrain-status", "UNAVAILABLE");
    }
}

// --------------------------------------------------
// RESET MAP
// --------------------------------------------------

function resetPoints() {
    setPoint("start", DEFAULT_START[0], DEFAULT_START[1]);
    setPoint("end", DEFAULT_END[0], DEFAULT_END[1]);
    setClickMode("start");
}

const resetButton = element("reset-map");

if (resetButton) {
    resetButton.addEventListener("click", () => {
        map.getView().animate({
            center: JEZERO,
            zoom: DEFAULT_ZOOM,
            duration: 700
        });

        routeSource.clear();
        resetPoints();

        updateCoordinates(DEFAULT_START[0], DEFAULT_START[1]);
        inspectTerrain(DEFAULT_START[0], DEFAULT_START[1]);

        updateText(
            "route-results",
            "Click the map or a science stop to set the start and destination, then calculate a route for a GO / NO-GO verdict."
        );
    });
}

// --------------------------------------------------
// BACKEND HEALTH CHECK
// --------------------------------------------------

async function checkBackendHealth() {
    const statusElement = element("backend-status");

    try {
        const response = await fetch(
            `${API_BASE}/api/health`
        );

        if (!response.ok) {
            throw new Error("Backend health check failed.");
        }

        const data = await response.json();

        if (statusElement) {
            statusElement.textContent =
                ["online", "success", "ok"].includes(data.status)
                    ? "ONLINE"
                    : "CHECK STATUS";
        }

        console.log("MARSWARD backend status:", data);

    } catch (error) {
        console.error("Backend connection error:", error);

        if (statusElement) {
            statusElement.textContent = "OFFLINE";
        }
    }
}

// --------------------------------------------------
// NASA MAP TILE STATUS
// --------------------------------------------------

terrainSource.on("tileloadend", () => {
    updateText("map-status", "NASA MOLA DATA LOADED");
});

terrainSource.on("tileloaderror", () => {
    updateText("map-status", "NASA MAP TILE ERROR");
});

// --------------------------------------------------
// ROUTE PLANNER
// --------------------------------------------------

function convertRoutePoint(point) {
    if (!Array.isArray(point) || point.length < 2) {
        return null;
    }

    const first = Number(point[0]);
    const second = Number(point[1]);

    if (!Number.isFinite(first) || !Number.isFinite(second)) {
        return null;
    }

    // If the backend already returned longitude/latitude,
    // use those coordinates directly.

    if (
        first >= -180 &&
        first <= 180 &&
        second >= -90 &&
        second <= 90 &&
        isInsideJezero(first, second)
    ) {
        return [first, second];
    }

    // Otherwise interpret the point as a grid coordinate
    // from the 40 x 40 route-planning grid.

    const gridSize = 40;

    const lon =
        JEZERO_BOUNDS.west +
        (first / (gridSize - 1)) *
        (JEZERO_BOUNDS.east - JEZERO_BOUNDS.west);

    const lat =
        JEZERO_BOUNDS.north -
        (second / (gridSize - 1)) *
        (JEZERO_BOUNDS.north - JEZERO_BOUNDS.south);

    return [lon, lat];
}

// Travel mode presets fill the speed field.
element("eva-mode")?.addEventListener("change", (event) => {
    const speed = event.target.selectedOptions[0]?.dataset.speed;

    if (speed && element("eva-speed")) {
        element("eva-speed").value = speed;
    }
});

function numberOrNull(id) {
    const input = element(id);

    if (!input || input.value.trim() === "") {
        return null;
    }

    const value = Number(input.value);

    return Number.isFinite(value) ? value : null;
}

function readEvaSettings() {
    return {
        travel_mode: element("eva-mode")?.value || "foot",
        speed_kmh: numberOrNull("eva-speed"),
        time_limit_hours: numberOrNull("eva-limit"),
        time_at_site_hours: numberOrNull("eva-site"),
        reserve_hours: numberOrNull("eva-reserve"),
        max_slope_degrees: numberOrNull("eva-slope"),
        dust_opacity: numberOrNull("eva-dust"),
        air_temperature_c: numberOrNull("eva-temp"),
        round_trip: element("eva-round-trip")?.checked ?? true
    };
}

const VERDICT_STYLES = {
    GO: { cssClass: "go", label: "GO", color: "#3dffa0" },
    CAUTION: { cssClass: "caution", label: "CAUTION", color: "#ffd23f" },
    NO_GO: { cssClass: "nogo", label: "NO-GO", color: "#ff4d5e" }
};

function formatHours(hours) {
    if (hours === null || hours === undefined || !Number.isFinite(Number(hours))) {
        return "N/A";
    }

    const minutes = Math.round(Math.abs(hours) * 60);
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    const sign = hours < 0 ? "−" : "";

    if (h && m) {
        return `${sign}${h} h ${m} min`;
    }

    return h ? `${sign}${h} h` : `${sign}${m} min`;
}

function renderVerdict(verdict, route) {
    const target = element("route-results");

    if (!target || !verdict) {
        return;
    }

    const style = VERDICT_STYLES[verdict.status] || VERDICT_STYLES.CAUTION;

    // The headline starts with the status word; the badge shows it.
    const headline = String(verdict.headline || "").replace(/^[A-Z-]+:\s*/, "");

    // Skip the reason already shown as the headline.
    const reasons = (verdict.reasons || [])
        .filter(reason => reason.message !== headline)
        .map(reason => `
        <li class="${escapeHtml(reason.level)}">${escapeHtml(reason.message)}</li>
    `).join("");

    const stat = (label, value) =>
        `<span class="route-stat">${label}: <strong>${escapeHtml(value)}</strong></span>`;

    let stats = "";

    if (verdict.timing && verdict.terrain) {
        const timing = verdict.timing;
        const terrain = verdict.terrain;

        stats = `
            <div class="route-stats">
                ${stat("One way", `${formatNumber(terrain.one_way_distance_km, 1)} km`)}
                ${stat("Total distance", `${formatNumber(terrain.total_distance_km, 1)} km`)}
                ${stat("Out", formatHours(timing.outbound_hours))}
                ${stat("Back", formatHours(timing.return_hours))}
                ${stat("At destination", formatHours(timing.time_at_site_hours))}
                ${stat("Total time", formatHours(timing.total_hours))}
                ${stat("Spare", formatHours(timing.spare_hours))}
                ${stat("Steepest slope", `${formatNumber(terrain.steepest_slope_degrees, 1)}°`)}
                ${stat("Climb on the way out", `${formatNumber(terrain.ascent_m, 0)} m`)}
                ${stat("Descent on the way out", `${formatNumber(terrain.descent_m, 0)} m`)}
                ${route ? stat("Cells searched", route.visited_nodes ?? "N/A") : ""}
            </div>
        `;
    }

    const assumptions = (verdict.assumptions || []).length
        ? `
            <details class="verdict-assumptions">
                <summary>Assumptions behind this verdict</summary>
                <ul>${verdict.assumptions.map(text => `<li>${escapeHtml(text)}</li>`).join("")}</ul>
            </details>
        `
        : "";

    target.innerHTML = `
        <div class="verdict ${style.cssClass}">
            <span class="verdict-badge">${style.label}</span>
            <div class="verdict-body">
                <strong>${escapeHtml(headline)}</strong>
                <ul class="verdict-reasons">${reasons}</ul>
            </div>
        </div>
        ${stats}
        ${assumptions}
    `;
}

async function generateRoute() {
    const [startLon, startLat] = readPoint("start");
    const [endLon, endLat] = readPoint("end");

    const resultsElement = element("route-results");

    if (
        !Number.isFinite(startLon) ||
        !Number.isFinite(startLat) ||
        !Number.isFinite(endLon) ||
        !Number.isFinite(endLat)
    ) {
        if (resultsElement) {
            resultsElement.textContent =
                "Please enter valid starting and destination coordinates.";
        }

        return;
    }

    if (
        !isInsideJezero(startLon, startLat) ||
        !isInsideJezero(endLon, endLat)
    ) {
        if (resultsElement) {
            resultsElement.textContent =
                `Both locations must be within the study area (${boundsText()}).`;
        }

        return;
    }

    if (resultsElement) {
        resultsElement.textContent = "Calculating route and verdict...";
    }

    const routeButton = element("generate-route");

    if (routeButton) {
        routeButton.disabled = true;
    }

    try {
        const response = await fetch(
            `${API_BASE}/api/route`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    start: [startLon, startLat],
                    destination: [endLon, endLat],
                    eva: readEvaSettings()
                })
            }
        );

        let data = null;

        try {
            data = await response.json();
        } catch (parseError) {
            data = null;
        }

        if (!response.ok) {
            throw new Error(
                (data && data.error) || `Route API returned ${response.status}`
            );
        }

        routeSource.clear();

        drawPoint("start", startLon, startLat);
        drawPoint("end", endLon, endLat);

        // No route within the slope limit: the verdict is NO-GO.
        if (data.status === "no_route") {
            renderVerdict(data.verdict, null);
            return;
        }

        const route = data.route;

        if (!route || !route.path || route.path.length === 0) {
            throw new Error("The route planner did not return a valid path.");
        }

        const routeCoordinates = route.path
            .map(convertRoutePoint)
            .filter(point => point !== null);

        if (routeCoordinates.length === 0) {
            throw new Error("Could not convert the returned route coordinates.");
        }

        // Join the route to the exact start and destination, since
        // the path itself runs between MOLA pixel centres.
        routeCoordinates.unshift([startLon, startLat]);
        routeCoordinates.push([endLon, endLat]);

        const verdictStyle = VERDICT_STYLES[data.verdict?.status];

        const routeFeature = new Feature({
            geometry: new LineString(routeCoordinates),
            color: verdictStyle ? verdictStyle.color : "#ff9f43"
        });

        routeSource.addFeature(routeFeature);

        map.getView().fit(routeFeature.getGeometry(), {
            padding: [70, 70, 70, 70],
            duration: 700,
            maxZoom: 11
        });

        renderVerdict(data.verdict, route);

        console.log("MARSWARD route result:", data);

    } catch (error) {
        console.error("Route generation error:", error);

        if (resultsElement) {
            resultsElement.textContent =
                `Could not generate route: ${error.message}`;
        }

    } finally {
        if (routeButton) {
            routeButton.disabled = false;
        }
    }
}

const routeButton = element("generate-route");

if (routeButton) {
    routeButton.addEventListener("click", generateRoute);
}

// --------------------------------------------------
// VIEW SWITCHING (events sent by modules.js)
// --------------------------------------------------

window.addEventListener("marsward:view", (event) => {
    const { view, mode } = event.detail || {};

    if (view !== "map") {
        return;
    }

    setMapMode(mode);

    // The map was hidden or resized, so recalculate its size.
    map.updateSize();

    if (mode === "route") {
        element("start-lon")?.focus();
    }

    // Hazard Analysis shows the whole study region.
    if (mode === "hazard") {
        map.getView().fit(regionExtent(), {
            padding: [20, 20, 20, 20],
            duration: 400
        });
    }
});

// --------------------------------------------------
// INITIALIZE DASHBOARD
// --------------------------------------------------

resetPoints();

updateCoordinates(DEFAULT_START[0], DEFAULT_START[1]);

checkBackendHealth();
loadTerrainSummary();
loadScienceStops();
refreshBlockedTerrain();
inspectTerrain(DEFAULT_START[0], DEFAULT_START[1]);

console.log("MARSWARD mission-control frontend initialized.");