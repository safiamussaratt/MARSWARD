
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

// --------------------------------------------------
// CONFIGURATION
// --------------------------------------------------

const JEZERO = [77.7, 18.4];

const JEZERO_BOUNDS = {
    west: 74,
    east: 81,
    south: 16,
    north: 21
};

const NASA_TILE_URL =
    "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg";

const API_BASE = "";

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
    imageSize: [448, 320]
});

const hazardLayer = new ImageLayer({
    source: hazardSource,
    opacity: 1,
    visible: true,
    zIndex: 2
});

// --------------------------------------------------
// ROUTE AND MARKER LAYERS
// --------------------------------------------------

const routeSource = new VectorSource();

const routeLayer = new VectorLayer({
    source: routeSource,
    zIndex: 3,
    style: new Style({
        stroke: new Stroke({
            color: "#ff9f43",
            width: 3
        })
    })
});

const markerSource = new VectorSource();

const markerLayer = new VectorLayer({
    source: markerSource,
    zIndex: 4,
    style: new Style({
        image: new CircleStyle({
            radius: 7,
            fill: new Fill({
                color: "#ff6b35"
            }),
            stroke: new Stroke({
                color: "#ffffff",
                width: 2
            })
        })
    })
});

// --------------------------------------------------
// MAP INITIALIZATION
// --------------------------------------------------

const map = new Map({
    target: "map",
    layers: [
        terrainLayer,
        hazardLayer,
        routeLayer,
        markerLayer
    ],
    view: new View({
        projection: marsProjection,
        center: JEZERO,
        zoom: 5,
        minZoom: 1,
        maxZoom: 8,
        extent: [-180, -90, 180, 90]
    })
});

// --------------------------------------------------
// MAP MARKER
// --------------------------------------------------

function addMarker(lon, lat) {
    markerSource.clear();

    const marker = new Feature({
        geometry: new Point([lon, lat])
    });

    markerSource.addFeature(marker);
}

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

    const startLon = element("start-lon");
    const startLat = element("start-lat");

    if (startLon && startLat) {
        startLon.value = lon.toFixed(4);
        startLat.value = lat.toFixed(4);
    }
}

// --------------------------------------------------
// TERRAIN INSPECTION
// --------------------------------------------------

async function inspectTerrain(lon, lat) {
    if (!isInsideJezero(lon, lat)) {
        updateText(
            "selected-region",
            "Outside Jezero Crater analysis area"
        );

        updateText(
            "terrain-inspection",
            "Select a location inside the Jezero Crater analysis area."
        );

        return;
    }

    updateText("selected-region", "Analyzing terrain...");

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

        updateText(
            "selected-region",
            "Jezero Crater"
        );

        updateText(
            "selected-location",
            `${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`
        );

        updateText(
            "terrain-inspection",
            `Elevation: ${formatNumber(terrain.elevation_metres, 1)} m | Slope: ${formatNumber(terrain.slope_degrees, 2)}° | Hazard: ${terrain.hazard_class}`
        );

        updateText(
            "terrain-elevation",
            `${formatNumber(terrain.elevation_metres, 1)} m`
        );

        updateText(
            "terrain-slope",
            `${formatNumber(terrain.slope_degrees, 2)}°`
        );

        updateText(
            "terrain-hazard",
            terrain.hazard_class || "Unknown"
        );

        updateText(
            "terrain-pixel",
            pixel
                ? `${pixel.latitude.toFixed(4)}°, ${pixel.longitude.toFixed(4)}°`
                : "N/A"
        );

        updateText(
            "terrain-raster-index",
            raster
                ? `Row ${raster.row}, Column ${raster.column}`
                : "N/A"
        );

        console.log("MARSWARD terrain inspection:", data);

    } catch (error) {
        console.error("Terrain inspection error:", error);

        updateText(
            "selected-region",
            "Terrain inspection unavailable"
        );

        updateText(
            "terrain-inspection",
            "Could not retrieve terrain information. Check the backend."
        );
    }
}

// --------------------------------------------------
// MAP CLICK EVENT
// --------------------------------------------------

map.on("click", function (event) {
    const [lon, lat] = event.coordinate;

    addMarker(lon, lat);
    updateCoordinates(lon, lat);
    inspectTerrain(lon, lat);
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

        const categories =
            data.hazards.summary.categories;

        // Elevation statistics

        updateText(
            "elevation-min",
            `${formatNumber(elevation.minimum, 0)} m`
        );

        updateText(
            "elevation-max",
            `${formatNumber(elevation.maximum, 0)} m`
        );

        updateText(
            "elevation-mean",
            `${formatNumber(elevation.mean, 1)} m`
        );

        updateText(
            "elevation-median",
            `${formatNumber(elevation.median, 0)} m`
        );

        // Slope statistics

        updateText(
            "slope-mean",
            `${formatNumber(slope.mean, 2)}°`
        );

        updateText(
            "slope-max",
            `${formatNumber(slope.maximum, 2)}°`
        );

        updateText(
            "slope-p90",
            `${formatNumber(slope.percentile_90, 2)}°`
        );

        // Hazard percentages

        updateText(
            "hazard-gentle",
            `${formatNumber(categories.Gentle.percentage, 2)}%`
        );

        updateText(
            "hazard-moderate",
            `${formatNumber(categories.Moderate.percentage, 2)}%`
        );

        updateText(
            "hazard-steep",
            `${formatNumber(categories.Steep.percentage, 2)}%`
        );

        updateText(
            "hazard-very-steep",
            `${formatNumber(categories["Very Steep"].percentage, 2)}%`
        );

        console.log("MARSWARD terrain summary:", data);

    } catch (error) {
        console.error("Terrain summary error:", error);

        updateText(
            "terrain-summary-status",
            "Terrain statistics unavailable"
        );
    }
}

// --------------------------------------------------
// RESET MAP
// --------------------------------------------------

const resetButton = element("reset-map");

if (resetButton) {
    resetButton.addEventListener("click", () => {
        map.getView().animate({
            center: JEZERO,
            zoom: 5,
            duration: 700
        });

        markerSource.clear();
        routeSource.clear();

        updateCoordinates(JEZERO[0], JEZERO[1]);

        inspectTerrain(JEZERO[0], JEZERO[1]);

        updateText(
            "selected-region",
            "Jezero Crater"
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
                data.status === "success" || data.status === "ok"
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

async function generateRoute() {
    const startLon = Number(element("start-lon")?.value);
    const startLat = Number(element("start-lat")?.value);

    const endLon = Number(element("end-lon")?.value);
    const endLat = Number(element("end-lat")?.value);

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
                "Both locations must be within the Jezero Crater analysis area (74°–81° E, 16°–21° N).";
        }

        return;
    }

    if (resultsElement) {
        resultsElement.textContent = "Calculating optimal route...";
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
                    destination: [endLon, endLat]
                })
            }
        );

        if (!response.ok) {
            throw new Error(`Route API returned ${response.status}`);
        }

        const data = await response.json();

        if (data.status === "error") {
            throw new Error(data.message || "Route generation failed.");
        }

        const route = data.route || data;

        if (!route.path || route.path.length === 0) {
            throw new Error("The route planner did not return a valid path.");
        }

        const routeCoordinates = route.path
            .map(convertRoutePoint)
            .filter(point => point !== null);

        if (routeCoordinates.length === 0) {
            throw new Error("Could not convert the returned route coordinates.");
        }

        routeSource.clear();
        markerSource.clear();

        const routeFeature = new Feature({
            geometry: new LineString(routeCoordinates)
        });

        routeSource.addFeature(routeFeature);

        // Add start and destination markers.

        markerSource.addFeature(
            new Feature({
                geometry: new Point([startLon, startLat])
            })
        );

        markerSource.addFeature(
            new Feature({
                geometry: new Point([endLon, endLat])
            })
        );

        map.getView().fit(routeFeature.getGeometry(), {
            padding: [60, 60, 60, 60],
            duration: 700,
            maxZoom: 7
        });

        if (resultsElement) {
            resultsElement.innerHTML = `
                <strong>Route generated successfully</strong>
                <p>Distance: ${formatNumber(route.distance_grid_units, 2)} grid units</p>
                <p>Terrain cost: ${formatNumber(route.terrain_cost, 2)}</p>
                <p>Visited nodes: ${route.visited_nodes ?? "N/A"}</p>
                <p>Algorithm: ${route.model || "A*"}</p>
                <p>Grid size: ${route.grid_size || "40 × 40"}</p>
            `;
        }

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
// INITIALIZE DASHBOARD
// --------------------------------------------------

updateCoordinates(JEZERO[0], JEZERO[1]);

addMarker(JEZERO[0], JEZERO[1]);

checkBackendHealth();
loadTerrainSummary();
inspectTerrain(JEZERO[0], JEZERO[1]);

console.log("MARSWARD mission-control frontend initialized.");
