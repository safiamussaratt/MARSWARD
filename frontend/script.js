

import Map from "https://esm.sh/ol@10.6.1/Map.js";
import View from "https://esm.sh/ol@10.6.1/View.js";
import TileLayer from "https://esm.sh/ol@10.6.1/layer/Tile.js";
import XYZ from "https://esm.sh/ol@10.6.1/source/XYZ.js";
import TileGrid from "https://esm.sh/ol@10.6.1/tilegrid/TileGrid.js";
import Projection from "https://esm.sh/ol@10.6.1/proj/Projection.js";
import VectorLayer from "https://esm.sh/ol@10.6.1/layer/Vector.js";
import VectorSource from "https://esm.sh/ol@10.6.1/source/Vector.js";
import Feature from "https://esm.sh/ol@10.6.1/Feature.js";
import Point from "https://esm.sh/ol@10.6.1/geom/Point.js";
import Style from "https://esm.sh/ol@10.6.1/style/Style.js";
import CircleStyle from "https://esm.sh/ol@10.6.1/style/Circle.js";
import Fill from "https://esm.sh/ol@10.6.1/style/Fill.js";
import Stroke from "https://esm.sh/ol@10.6.1/style/Stroke.js";

import LineString from "https://esm.sh/ol@10.6.1/geom/LineString.js";

console.log("MARSWARD JavaScript initialized");

const JEZERO = [77.7, 18.4];

const marsProjection = new Projection({
    code: "MARS:EQ",
    units: "degrees",
    extent: [-180, -90, 180, 90]
});

const resolutions = Array.from(
    { length: 9 },
    (_, zoom) => 360 / (512 * Math.pow(2, zoom))
);

const tileGrid = new TileGrid({
    extent: [-180, -90, 180, 90],
    origin: [-180, 90],
    resolutions: resolutions,
    tileSize: 256
});

// NASA MOLA global color hillshade
const nasaSource = new XYZ({
    url:
        "https://trek.nasa.gov/tiles/Mars/EQ/" +
        "Mars_MGS_MOLA_ClrShade_merge_global_463m/" +
        "1.0.0/default/default028mm/{z}/{y}/{x}.jpg",

    projection: marsProjection,
    tileGrid: tileGrid,
    wrapX: false,
    crossOrigin: "anonymous"
});

const terrainLayer = new TileLayer({
    source: nasaSource
});

const markerSource = new VectorSource();

const markerLayer = new VectorLayer({
    source: markerSource,

    style: new Style({
        image: new CircleStyle({
            radius: 8,
            fill: new Fill({
                color: "#f08b56"
            }),
            stroke: new Stroke({
                color: "#ffffff",
                width: 2
            })
        })
    })
});

const routeSource = new VectorSource();

const routeLayer = new VectorLayer({
    source: routeSource,

    style: new Style({
        stroke: new Stroke({
            color: "#55d68b",
            width: 4
        })
    })
});

const map = new Map({
    target: "map",

    layers: [
        terrainLayer,
        routeLayer,
        markerLayer
    ],

    view: new View({
        projection: marsProjection,
        center: JEZERO,
        zoom: 4,
        minZoom: 0,
        maxZoom: 8,
        extent: [-180, -90, 180, 90]
    })
});

function updateCoordinates(longitude, latitude) {
    const latDirection = latitude >= 0 ? "N" : "S";
    const lonDirection = longitude >= 0 ? "E" : "W";

    document.getElementById("latitude").textContent =
        `${Math.abs(latitude).toFixed(4)}° ${latDirection}`;

    document.getElementById("longitude").textContent =
        `${Math.abs(longitude).toFixed(4)}° ${lonDirection}`;

    document.getElementById("map-coordinates").textContent =
        `LAT: ${latitude.toFixed(4)} | LON: ${longitude.toFixed(4)}`;
}

// Select a location by clicking the map
map.on("singleclick", function (event) {
    const [longitude, latitude] = event.coordinate;

    markerSource.clear();

    const selectedPoint = new Feature({
        geometry: new Point([longitude, latitude])
    });

    markerSource.addFeature(selectedPoint);

    updateCoordinates(longitude, latitude);
});

// Reset map to Jezero Crater
document.getElementById("reset-map").addEventListener("click", () => {
    map.getView().animate({
        center: JEZERO,
        zoom: 4,
        duration: 500
    });

    markerSource.clear();
    updateCoordinates(JEZERO[0], JEZERO[1]);
});

// Check Flask backend
async function checkBackend() {
    const status = document.getElementById("backend-status");

    try {
        const response = await fetch("/api/health");

        if (!response.ok) {
            throw new Error("Backend unavailable");
        }

        status.textContent = "ONLINE";
    } catch (error) {
        status.textContent = "OFFLINE";
    }
}

// Check NASA tile loading
nasaSource.on("tileloadend", () => {
    document.getElementById("map-status").textContent = "CONNECTED";
});

nasaSource.on("tileloaderror", () => {
    document.getElementById("map-status").textContent = "TILE ERROR";
});

updateCoordinates(JEZERO[0], JEZERO[1]);
checkBackend();


async function generateSafeRoute() {

    const button = document.getElementById("generate-route");
    const results = document.getElementById("route-results");

    const startLon = Number(
        document.getElementById("start-lon").value
    );

    const startLat = Number(
        document.getElementById("start-lat").value
    );

    const endLon = Number(
        document.getElementById("end-lon").value
    );

    const endLat = Number(
        document.getElementById("end-lat").value
    );

    const coordinates = [
        startLon, startLat,
        endLon, endLat
    ];

    if (!coordinates.every(Number.isFinite)) {
        results.textContent = "Please enter valid coordinates.";
        return;
    }

    if (
        startLon === endLon &&
        startLat === endLat
    ) {
        results.textContent =
            "Start and destination must be different.";
        return;
    }

    button.disabled = true;
    results.textContent = "Calculating optimized route...";

    try {

        const response = await fetch("/api/route", {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                start: [startLon, startLat],
                destination: [endLon, endLat]
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Route calculation failed.");
        }

        const route = data.route;

        routeSource.clear();

        const routeFeature = new Feature({
            geometry: new LineString(route.path)
        });

        routeSource.addFeature(routeFeature);

        // Add starting and destination markers
        markerSource.clear();

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

        // Zoom to display the calculated route
        map.getView().fit(
            routeFeature.getGeometry(),
            {
                padding: [70, 70, 70, 70],
                maxZoom: 6,
                duration: 700
            }
        );

        results.innerHTML = `
            <strong>ROUTE CALCULATED SUCCESSFULLY</strong>
            <br>
            <span class="route-stat">
                <strong>${route.path.length}</strong> Waypoints
            </span>
            <span class="route-stat">
                <strong>${route.distance_grid_units}</strong> Grid Units
            </span>
            <span class="route-stat">
                <strong>${route.terrain_cost}</strong> Terrain Cost
            </span>
            <br>
            <span style="color:#d69b78">
                Terrain model: ${route.model}
            </span>
        `;

    } catch (error) {

        console.error("Route error:", error);

        results.textContent = error.message;

    } finally {

        button.disabled = false;

    }
}

document
    .getElementById("generate-route")
    .addEventListener("click", generateSafeRoute);
