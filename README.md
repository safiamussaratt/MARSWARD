# MARSWARD

A mission-planning dashboard for Jezero Crater on Mars. It shows real NASA elevation data on a map, rates the terrain by slope, finds a route between two points, and gives a GO / CAUTION / NO-GO verdict for the trip with the reasons behind it.

## What it does

- **Martian Explorer**: pan-and-zoom map of Jezero. Click anywhere in the study area (74–81° E, 16–21° N) for elevation, slope and hazard class.
- **Hazard Analysis**: colored overlay rating every map square as Gentle (0–5°), Moderate (5–15°), Steep (15–25°) or Very Steep (over 25°).
- **Route Planner**: click the map to set a start and destination, or click a named science stop. The route avoids steep ground and never crosses squares above the slope limit (20° by default).
- **GO / NO-GO verdict**: for each route, compares travel time (slower on slopes) plus time at the destination against the time limit, and checks the steepest slope, dust and air temperature.
- **Survival Simulator**: checks whether water, food and oxygen supplies last a mission for a given crew, with an emergency reserve.
- **Science Explorer**: facts on Mars, Jezero and the dataset, six science stops, surface conditions from Perseverance, and terrain statistics.

## Data sources

| Data | Source |
|---|---|
| Elevation | NASA Mars Global Surveyor MOLA, MEGDR tile `megt90n000gb.img` (64 pixels per degree, about 926 m per pixel) |
| Base map | NASA Mars Trek MOLA color shaded-relief tiles |
| Surface conditions | Perseverance MEDA weather station, first 250 sols (Rodríguez-Manfredi et al., Nature Geoscience, 2023, https://doi.org/10.1038/s41561-022-01084-0) |

## How to run

1. Install Python 3.10 or later.
2. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Download `megt90n000gb.img` (about 133 MB) from the NASA PDS Geosciences Node MOLA MEGDR archive and place it at `data/terrain/megt90n000gb.img`. It is not stored in the repository because of its size.
4. Start the app:

   ```
   python app.py
   ```

5. Open http://127.0.0.1:5000 in a browser. An internet connection is needed for the map tiles and the map library.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Backend status |
| `GET /api/terrain/summary` | Elevation, slope and hazard statistics |
| `GET /api/terrain/inspect?lon=&lat=` | Terrain at one point |
| `GET /api/terrain/hazard-overlay` | Hazard overlay image |
| `POST /api/route` | Route and verdict. Body: `start`, `destination`, optional `eva` settings |
| `GET /api/science/stops` | Named science stops |
| `GET /api/science/overview` | Everything the Science Explorer shows |
| `GET /api/survival/defaults`, `POST /api/survival/simulate` | Survival Simulator |

## Limitations

- **Resolution.** Each elevation pixel is about 926 m wide. Slopes are regional averages; boulders, scarps and sand are not seen. A 3 km walk covers only three or four pixels.
- **Thresholds are prototypes.** The slope limit, the dust and cold thresholds, walking and rover speeds, and the survival consumption rates are planning assumptions, not validated mission limits.
- **Speed model.** Slowing on slopes uses the shape of Tobler's hiking function, an Earth walking model.
- **Science stop positions.** Only the landing site and crater center are precise; the other stops are placed approximately from published mission maps.
- **Dust and temperature are entered by the user.** The app shows Perseverance reference values but does not load a live weather feed.
