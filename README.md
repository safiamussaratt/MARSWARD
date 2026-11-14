# MARSWARD

**Team Space Case · NASA Space Apps Challenge 2026 (Karachi) · Challenge: Interplanetary Survival Guide: Martian Map**

A mission-planning dashboard for Jezero Crater on Mars. It shows real NASA elevation data on a map, rates the terrain by slope, finds a route between two points, and gives a GO / CAUTION / NO-GO verdict for the trip with the reasons behind it.

## What it does

- **Martian Explorer**: pan-and-zoom map of Jezero. Click anywhere in the study area (74–81° E, 16–21° N) for elevation, slope and hazard class.
- **Hazard Analysis**: colored overlay rating every map square as Gentle (0–5°), Moderate (5–15°), Steep (15–25°) or Very Steep (over 25°). A slope-limit slider marks in magenta the squares the route planner refuses to cross, with their count and area.
- **Route Planner**: click the map to set a start and destination, or click a named science stop. The route avoids steep ground and never crosses squares above the slope limit (20° by default).
- **GO / NO-GO verdict**: for each route, compares travel time (slower on slopes) plus time at the destination against the time limit, and checks the steepest slope, dust and air temperature.
- **Survival Simulator**: checks whether water, food and oxygen supplies last a mission for a given crew, with an emergency reserve.
- **Science Explorer**: facts on Mars, Jezero and the dataset, six science stops, surface conditions from Perseverance, and terrain statistics.

## How to use it

1. **Pick a trip.** On the map, the first click sets the start (orange) and the next click sets the destination (blue). Clicking a yellow science stop, or "Set as destination" in Science Explorer, also sets the destination.
2. **Set the conditions.** Choose on foot or crew rover, then adjust speed, time limit, time at the destination, time reserve, slope limit, dust opacity and air temperature.
3. **Calculate.** "Calculate Safe Route" draws the route and shows the verdict with its reasons, distances, times and the steepest slope.

Three trips that show the verdict changing, all starting from the Perseverance landing site:

| Trip | Result |
|---|---|
| To Three Forks on foot (the default) | GO, 4 h 52 min to spare |
| To Neretva Vallis on foot | NO-GO, about 5 hours over the 8-hour limit |
| Any trip with dust opacity set to 2 | NO-GO, storm-level dust |

## Data sources

| Data | Source |
|---|---|
| Elevation | NASA Mars Global Surveyor MOLA, MEGDR tile `megt90n000gb.img` (64 pixels per degree, about 926 m per pixel) |
| Place names and positions | IAU Gazetteer of Planetary Nomenclature (USGS) |
| Base map | NASA Mars Trek MOLA color shaded-relief tiles |
| Surface conditions | Perseverance MEDA weather station, first 250 sols (Rodríguez-Manfredi et al., Nature Geoscience, 2023, https://doi.org/10.1038/s41561-022-01084-0) |

## How to run

1. Install Python 3.10 or later.
2. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Start the app:

   ```
   python app.py
   ```

4. Open http://127.0.0.1:5000 in a browser. An internet connection is needed for the map tiles and the map library.

The Jezero elevation data is included in the repository as `data/terrain/jezero_region.npz` (about 230 KB), cut from the NASA tile, so no download is needed.

To rebuild that file from the full tile, download `megt90n000gb.img` (about 133 MB) from the NASA PDS Geosciences Node MOLA MEGDR archive, place it in `data/terrain/`, and run:

```
python -m backend.build_region_crop
```

## Project structure

```
MARSWARD/
├── app.py                      Flask server and API routes
├── requirements.txt
├── backend/
│   ├── mars_data.py            Terrain loading (the one file to edit for a new dataset)
│   ├── build_region_crop.py    Rebuilds the bundled Jezero data file
│   ├── terrain_processor.py    Slope calculation
│   ├── hazard_analyzer.py      Slope classes
│   ├── terrain_service.py      Terrain statistics, point inspection, overlay image
│   ├── run_terrain_analysis.py Saves terrain results to results/terrain/
│   ├── route_optimizer.py      A* route search with a slope limit
│   ├── eva_planner.py          GO / CAUTION / NO-GO verdict
│   ├── survival_simulator.py   Water, food and oxygen check
│   ├── science_stops.py        Named stops and surface conditions
│   └── science_service.py      Science Explorer content
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── script.js               Map, route planner and verdict
│   └── modules.js              Navigation, Survival Simulator, Science Explorer
├── data/terrain/
│   └── jezero_region.npz       Jezero elevation data (bundled)
└── tests/
```

Built with Python, Flask and NumPy on the server, and OpenLayers for the map.

## Changing the dataset

All terrain comes from one function, `get_region()` in `backend/mars_data.py`. Slopes, hazards, routes, the map overlay and the Science Explorer read from it, and the page gets the region's bounds and size from `/api/config`. To use a different elevation dataset:

1. Load the new elevation grid as a 2D array (north at the top) with its bounds and pixels per degree.
2. Pass it to `build_region()` and `save_region_file()`, replacing `jezero_region.npz`.
3. Update `DATASET_INFO` at the top of `backend/mars_data.py`.

The science stops in `backend/science_stops.py` are specific to Jezero and need updating if the region changes.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Backend status |
| `GET /api/config` | Region bounds, raster size and dataset name |
| `GET /api/terrain/summary` | Elevation, slope and hazard statistics |
| `GET /api/terrain/inspect?lon=&lat=` | Terrain at one point |
| `GET /api/terrain/hazard-overlay` | Hazard overlay image |
| `GET /api/terrain/blocked-overlay?max_slope=` | Image of squares above a slope limit |
| `GET /api/terrain/blocked-summary?max_slope=` | Count and area of those squares |
| `POST /api/route` | Route and verdict. Body: `start`, `destination`, optional `eva` settings |
| `GET /api/science/stops` | Named science stops |
| `GET /api/science/overview` | Everything the Science Explorer shows |
| `GET /api/survival/defaults`, `POST /api/survival/simulate` | Survival Simulator |

## Limitations

- **Resolution.** Each elevation pixel is about 926 m wide. Slopes are regional averages; boulders, scarps and sand are not seen. A 3 km walk covers only three or four pixels.
- **Limits are planning choices.** The slope limit, cold threshold, time limit and travel speeds are editable assumptions. The dust limits (caution above 0.8, NO-GO at 2) match levels Perseverance measured in the January 2022 dust storm (Lemmon et al., Geophysical Research Letters, 2022, https://doi.org/10.1029/2022GL100126); using them as limits is our choice.
- **Survival rates.** Defaults are 0.84 kg oxygen, 3.54 kg water and 1.77 kg food per person per day, from NASA crew metabolic figures and the Life Support Baseline Values and Assumptions Document (NASA/TP-2015-218570), taken from secondary sources.
- **Speed model.** Slowing on slopes uses the shape of Tobler's hiking function, an Earth walking model.
- **Science stop positions.** The landing site uses published coordinates; the crater center, Neretva Vallis and Pliva Vallis use IAU gazetteer feature centers; Three Forks and Western Delta Top are placed approximately from mission maps.
- **Dust and temperature are entered by the user.** The app shows Perseverance reference values but does not load a live weather feed.
