import os
import numpy as np


# NASA MOLA MEGDR dataset configuration

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "terrain",
    "megt90n000gb.img"
)

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


def load_mola_data():
    """
    Load the NASA MOLA elevation raster.

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
    Extract a geographical region from the MOLA raster.

    Dataset coverage:
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

    col_start = int(
        np.floor(west_lon * PIXELS_PER_DEGREE)
    )

    col_end = int(
        np.ceil(east_lon * PIXELS_PER_DEGREE)
    )

    row_start = int(
        np.floor(
            (90 - north_lat) * PIXELS_PER_DEGREE
        )
    )

    row_end = int(
        np.ceil(
            (90 - south_lat) * PIXELS_PER_DEGREE
        )
    )

    region = elevation[
        row_start:row_end,
        col_start:col_end
    ].astype(np.float32)

    if region.size == 0:
        raise ValueError("The extracted MOLA region is empty.")

    # Coordinates represent pixel centres.
    rows = np.arange(row_start, row_end)
    columns = np.arange(col_start, col_end)

    latitudes = 90 - (
        rows + 0.5
    ) / PIXELS_PER_DEGREE

    longitudes = (
        columns + 0.5
    ) / PIXELS_PER_DEGREE

    return {
        "elevation": region,
        "latitudes": latitudes,
        "longitudes": longitudes,
        "bounds": {
            "west": west_lon,
            "east": east_lon,
            "south": south_lat,
            "north": north_lat
        }
    }


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


def coordinates_to_pixel(longitude, latitude, bounds=None):
    """
    Convert longitude/latitude to the nearest pixel
    in an extracted MOLA region.

    Returns:
        (column, row)
    """

    if bounds is None:
        bounds = JEZERO_BOUNDS

    column = round(
        (longitude - bounds["west"])
        * PIXELS_PER_DEGREE - 0.5
    )

    row = round(
        (bounds["north"] - latitude)
        * PIXELS_PER_DEGREE - 0.5
    )

    return column, row


def pixel_to_coordinates(column, row, bounds=None):
    """
    Convert a pixel location into its geographic
    pixel-centre coordinates.

    Returns:
        [longitude, latitude]
    """

    if bounds is None:
        bounds = JEZERO_BOUNDS

    longitude = (
        bounds["west"]
        + (column + 0.5) / PIXELS_PER_DEGREE
    )

    latitude = (
        bounds["north"]
        - (row + 0.5) / PIXELS_PER_DEGREE
    )

    return [
        float(longitude),
        float(latitude)
    ]


if __name__ == "__main__":

    print("\n===================================")
    print("       MARSWARD - NASA MOLA")
    print("===================================")

    print("\nLoading NASA elevation dataset...")

    elevation = load_mola_data()

    print("Dataset loaded successfully!")
    print("Full raster dimensions:", elevation.shape)

    print("\nExtracting Jezero Crater region...")

    jezero = extract_region(elevation)

    print("Region extracted successfully!")

    print("\nCalculating elevation statistics...")

    stats = get_elevation_statistics(jezero)

    print("\n========== JEZERO TERRAIN ==========")
    print("Region dimensions:", stats["shape"])
    print("Minimum elevation:", stats["minimum"], "m")
    print("Maximum elevation:", stats["maximum"], "m")
    print("Mean elevation:", round(stats["mean"], 2), "m")
    print("Median elevation:", round(stats["median"], 2), "m")
    print("Zero-valued pixels:", stats["zero_value_count"])

    print("\n===================================")
    print("       DATA PROCESSING COMPLETE")
    print("===================================")