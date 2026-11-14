"""
MARSWARD terrain data access.

THIS IS THE ONE FILE TO EDIT WHEN THE DATASET CHANGES.

Every other module gets its terrain from get_region(), which
returns one dictionary:

    elevation           2D float32 array, metres, row 0 = north
    latitudes           1D array, pixel-centre latitude per row
    longitudes          1D array, pixel-centre longitude per column
    bounds              {"west", "east", "south", "north"} in degrees
    pixels_per_degree   raster resolution
    name                region name shown in the app
    dataset             DATASET_INFO (below)

get_region() looks for the small region file first
(data/terrain/jezero_region.npz, stored in the repository).
If it is missing, it falls back to the full NASA MOLA tile.

To switch to a different dataset:
  1. Write a loader that returns the elevation grid as a 2D
     array (north at the top) with its bounds and resolution.
  2. Save it with save_region_file(), or point REGION_PATH at it.
  3. Update DATASET_INFO.
Nothing else needs to change: slopes, hazards, routes, the map
overlay and the Science Explorer all read from get_region().
"""

import os

import numpy as np


# --------------------------------------------------
# DATASET DESCRIPTION (edit when the dataset changes)
# --------------------------------------------------

DATASET_INFO = {
    "name": "NASA MOLA MEGDR",
    "short_name": "NASA / MOLA",
    "instrument": (
        "Mars Orbiter Laser Altimeter (MOLA), Mars Global Surveyor"
    ),
    "product": "MEGDR (Mission Experiment Gridded Data Record)",
    "source_file": "megt90n000gb.img",
    "format": "16-bit signed integers, big-endian, metres"
}

REGION_NAME = "Jezero Crater"

TERRAIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "terrain"
)

# Small region file kept in the repository.
REGION_PATH = os.path.join(TERRAIN_DIR, "jezero_region.npz")

# Full NASA MOLA tile (133 MB, not in the repository).
DATA_PATH = os.path.join(TERRAIN_DIR, "megt90n000gb.img")

ROWS = 5760
COLUMNS = 11520
PIXELS_PER_DEGREE = 64

MARS_RADIUS_KM = 3396.0
MARS_RADIUS_METERS = 3_396_000.0

JEZERO_BOUNDS = {
    "west": 74.0,
    "east": 81.0,
    "south": 16.0,
    "north": 21.0
}


# --------------------------------------------------
# FULL MOLA TILE
# --------------------------------------------------

def load_mola_data():
    """
    Load the full NASA MOLA elevation raster.

    Data format:
    - Signed 16-bit integer
    - Big-endian
    - One band
    - 5760 rows x 11520 columns
    - Elevation values in metres
    """

    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"NASA MOLA dataset not found: {DATA_PATH}"
        )

    expected_size = ROWS * COLUMNS * 2
    actual_size = os.path.getsize(DATA_PATH)

    if actual_size != expected_size:
        raise ValueError(
            f"Unexpected dataset size: {actual_size} bytes. "
            f"Expected {expected_size} bytes."
        )

    elevation = np.memmap(
        DATA_PATH,
        dtype=">i2",
        mode="r",
        shape=(ROWS, COLUMNS)
    )

    return elevation


def extract_region(
    elevation,
    west_lon=74.0,
    east_lon=81.0,
    south_lat=16.0,
    north_lat=21.0
):
    """
    Extract a geographical region from the full MOLA raster.

    Tile coverage:
    Longitude: 0 to 180 degrees east
    Latitude: 0 to 90 degrees north

    Raster rows run north to south.
    Raster columns run west to east.
    """

    if not (
        0 <= west_lon < east_lon <= 180
        and 0 <= south_lat < north_lat <= 90
    ):
        raise ValueError("Invalid geographical boundaries.")

    col_start = int(np.floor(west_lon * PIXELS_PER_DEGREE))
    col_end = int(np.ceil(east_lon * PIXELS_PER_DEGREE))

    row_start = int(np.floor((90 - north_lat) * PIXELS_PER_DEGREE))
    row_end = int(np.ceil((90 - south_lat) * PIXELS_PER_DEGREE))

    region = elevation[
        row_start:row_end,
        col_start:col_end
    ].astype(np.float32)

    if region.size == 0:
        raise ValueError("The extracted MOLA region is empty.")

    return build_region(
        region,
        {
            "west": west_lon,
            "east": east_lon,
            "south": south_lat,
            "north": north_lat
        },
        PIXELS_PER_DEGREE
    )


# --------------------------------------------------
# REGION DICTIONARY AND REGION FILE
# --------------------------------------------------

def build_region(elevation, bounds, pixels_per_degree, name=REGION_NAME):
    """
    Build the region dictionary used across the app.

    elevation: 2D array, metres, row 0 at the northern edge.
    """

    elevation = np.asarray(elevation, dtype=np.float32)

    if elevation.ndim != 2 or elevation.size == 0:
        raise ValueError("Elevation must be a non-empty 2D array.")

    rows, columns = elevation.shape

    # Coordinates are pixel centres.
    latitudes = bounds["north"] - (
        np.arange(rows) + 0.5
    ) / pixels_per_degree

    longitudes = bounds["west"] + (
        np.arange(columns) + 0.5
    ) / pixels_per_degree

    return {
        "elevation": elevation,
        "latitudes": latitudes,
        "longitudes": longitudes,
        "bounds": {
            key: float(bounds[key])
            for key in ("west", "east", "south", "north")
        },
        "pixels_per_degree": float(pixels_per_degree),
        "name": name,
        "dataset": DATASET_INFO
    }


def save_region_file(region, path=REGION_PATH):
    """
    Save a region as a small compressed file for the repository.
    """

    bounds = region["bounds"]

    np.savez_compressed(
        path,
        elevation=np.round(region["elevation"]).astype(np.int16),
        bounds=np.array(
            [
                bounds["west"],
                bounds["east"],
                bounds["south"],
                bounds["north"]
            ],
            dtype=np.float64
        ),
        pixels_per_degree=np.float64(region["pixels_per_degree"]),
        name=np.str_(region.get("name", REGION_NAME))
    )


def load_region_file(path=REGION_PATH):
    """
    Load a region saved by save_region_file().
    """

    with np.load(path, allow_pickle=False) as data:

        west, east, south, north = (
            float(value) for value in data["bounds"]
        )

        return build_region(
            data["elevation"],
            {
                "west": west,
                "east": east,
                "south": south,
                "north": north
            },
            float(data["pixels_per_degree"]),
            name=str(data["name"])
        )


_REGION_CACHE = None


def get_region():
    """
    Return the terrain region the whole app works on.

    Uses the region file when present, otherwise extracts the
    region from the full MOLA tile. Loaded once per process.
    """

    global _REGION_CACHE

    if _REGION_CACHE is None:

        if os.path.exists(REGION_PATH):
            _REGION_CACHE = load_region_file(REGION_PATH)

        elif os.path.exists(DATA_PATH):
            _REGION_CACHE = extract_region(
                load_mola_data(),
                west_lon=JEZERO_BOUNDS["west"],
                east_lon=JEZERO_BOUNDS["east"],
                south_lat=JEZERO_BOUNDS["south"],
                north_lat=JEZERO_BOUNDS["north"]
            )

        else:
            raise FileNotFoundError(
                "No terrain data found. Expected "
                f"{REGION_PATH} or {DATA_PATH}."
            )

    return _REGION_CACHE


def pixel_size_meters(region=None):
    """
    North-south ground size of one pixel, in metres.
    """

    if region is None:
        region = get_region()

    return float(
        MARS_RADIUS_METERS
        * np.deg2rad(1.0 / region["pixels_per_degree"])
    )


def get_elevation_statistics(region):
    """
    Calculate basic elevation statistics in metres.
    """

    values = np.asarray(
        region["elevation"],
        dtype=np.float32
    )

    if values.size == 0:
        raise ValueError("Cannot calculate statistics for empty data.")

    return {
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "shape": values.shape,
        "zero_value_count": int(
            np.count_nonzero(values == 0)
        )
    }


# --------------------------------------------------
# COORDINATE CONVERSION
# --------------------------------------------------

def coordinates_to_pixel(longitude, latitude, bounds=None):
    """
    Convert longitude/latitude to the nearest pixel
    in the active region.

    Returns:
        (column, row)
    """

    region = get_region()

    if bounds is None:
        bounds = region["bounds"]

    pixels_per_degree = region["pixels_per_degree"]

    column = int(np.floor(
        (longitude - bounds["west"]) * pixels_per_degree
    ))

    row = int(np.floor(
        (bounds["north"] - latitude) * pixels_per_degree
    ))

    return column, row


def pixel_to_coordinates(column, row, bounds=None):
    """
    Convert a pixel location into its geographic
    pixel-centre coordinates.

    Returns:
        [longitude, latitude]
    """

    region = get_region()

    if bounds is None:
        bounds = region["bounds"]

    pixels_per_degree = region["pixels_per_degree"]

    longitude = (
        bounds["west"]
        + (column + 0.5) / pixels_per_degree
    )

    latitude = (
        bounds["north"]
        - (row + 0.5) / pixels_per_degree
    )

    return [
        float(longitude),
        float(latitude)
    ]


if __name__ == "__main__":

    region = get_region()
    stats = get_elevation_statistics(region)

    print("Dataset:", region["dataset"]["name"])
    print("Region:", region["name"], region["bounds"])
    print("Raster:", stats["shape"])
    print("Elevation:", stats["minimum"], "to", stats["maximum"], "m")