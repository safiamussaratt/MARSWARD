import numpy as np

from backend.mars_data import (
    load_mola_data,
    extract_region,
    get_elevation_statistics
)


# MOLA metadata:
# Mars reference radius = 3,396,000 metres
# Resolution = 1/64 degree per pixel

MARS_RADIUS_METERS = 3_396_000.0
PIXELS_PER_DEGREE = 64

PIXEL_SIZE_METERS = (
    MARS_RADIUS_METERS
    * np.deg2rad(1.0 / PIXELS_PER_DEGREE)
)


def validate_region(region):
    """
    Validate an extracted MOLA region.
    """

    if not isinstance(region, dict):
        raise TypeError("Region must be a dictionary.")

    required = (
        "elevation",
        "latitudes",
        "longitudes"
    )

    for key in required:
        if key not in region:
            raise ValueError(
                f"Missing region field: {key}"
            )

    elevation = np.asarray(
        region["elevation"]
    )

    latitudes = np.asarray(
        region["latitudes"]
    )

    longitudes = np.asarray(
        region["longitudes"]
    )

    if elevation.ndim != 2:
        raise ValueError(
            "Elevation data must be a 2D array."
        )

    rows, columns = elevation.shape

    if rows < 2 or columns < 2:
        raise ValueError(
            "Elevation data must have at least 2 rows and columns."
        )

    if len(latitudes) != rows:
        raise ValueError(
            "Latitude count does not match raster rows."
        )

    if len(longitudes) != columns:
        raise ValueError(
            "Longitude count does not match raster columns."
        )

    if not np.all(np.isfinite(elevation)):
        raise ValueError(
            "Elevation data contains invalid values."
        )

    if not np.all(np.isfinite(latitudes)):
        raise ValueError(
            "Latitude coordinates contain invalid values."
        )

    if not np.all(np.isfinite(longitudes)):
        raise ValueError(
            "Longitude coordinates contain invalid values."
        )

    if np.any(np.abs(latitudes) >= 90):
        raise ValueError(
            "Latitude must be between -90 and 90 degrees."
        )

    return (
        elevation.astype(np.float64),
        latitudes.astype(np.float64)
    )


def calculate_slope(region):
    """
    Calculate terrain slope from actual MOLA elevation data.

    Returns a 2D NumPy array of slope angles in degrees.

    East-west ground distance is adjusted for latitude.
    """

    elevation, latitudes = validate_region(region)

    edge_order = (
        2 if min(elevation.shape) >= 3 else 1
    )

    # North-south elevation gradient.
    dz_dy = np.gradient(
        elevation,
        PIXEL_SIZE_METERS,
        axis=0,
        edge_order=edge_order
    )

    # East-west ground distance changes with latitude.
    latitude_radians = np.deg2rad(latitudes)

    east_west_pixel_size = (
        PIXEL_SIZE_METERS
        * np.cos(latitude_radians)
    )

    if np.any(east_west_pixel_size <= 0):
        raise ValueError(
            "Invalid east-west pixel spacing."
        )

    # Elevation difference per column.
    dz_per_column = np.gradient(
        elevation,
        axis=1,
        edge_order=edge_order
    )

    # Convert elevation change to metres per metre.
    dz_dx = (
        dz_per_column
        / east_west_pixel_size[:, np.newaxis]
    )

    gradient_magnitude = np.sqrt(
        dz_dx ** 2 + dz_dy ** 2
    )

    slope = np.degrees(
        np.arctan(gradient_magnitude)
    )

    return slope.astype(np.float32)


def get_slope_statistics(slope):
    """
    Calculate descriptive statistics for a slope raster.
    """

    slope = np.asarray(
        slope,
        dtype=np.float64
    )

    if slope.ndim != 2 or slope.size == 0:
        raise ValueError(
            "Invalid slope raster."
        )

    if not np.all(np.isfinite(slope)):
        raise ValueError(
            "Slope raster contains invalid values."
        )

    return {
        "minimum": float(np.min(slope)),
        "maximum": float(np.max(slope)),
        "mean": float(np.mean(slope)),
        "median": float(np.median(slope)),
        "percentile_75": float(
            np.percentile(slope, 75)
        ),
        "percentile_90": float(
            np.percentile(slope, 90)
        ),
        "percentile_95": float(
            np.percentile(slope, 95)
        )
    }


def analyze_jezero():
    """
    Load MOLA data, extract Jezero, and calculate slope.
    """

    print("\nLoading NASA MOLA elevation data...")

    elevation = load_mola_data()

    print("Extracting Jezero Crater region...")

    region = extract_region(elevation)

    print("Calculating elevation statistics...")

    elevation_stats = get_elevation_statistics(region)

    print("Calculating terrain slope...")

    slope = calculate_slope(region)

    slope_stats = get_slope_statistics(slope)

    return {
        "region": region,
        "slope": slope,
        "elevation_statistics": elevation_stats,
        "slope_statistics": slope_stats
    }


if __name__ == "__main__":

    print("\n========================================")
    print("       MARSWARD TERRAIN PROCESSOR")
    print("========================================")

    results = analyze_jezero()

    elevation_stats = results["elevation_statistics"]
    slope_stats = results["slope_statistics"]

    print("\n========== ELEVATION RESULTS ==========")

    print("Raster dimensions:", elevation_stats["shape"])
    print("Minimum elevation:", elevation_stats["minimum"], "m")
    print("Maximum elevation:", elevation_stats["maximum"], "m")
    print("Mean elevation:", round(elevation_stats["mean"], 2), "m")
    print("Median elevation:", round(elevation_stats["median"], 2), "m")

    print("\n========== SLOPE RESULTS =============")

    print("Slope dimensions:", results["slope"].shape)
    print("Minimum slope:", round(slope_stats["minimum"], 3), "degrees")
    print("Maximum slope:", round(slope_stats["maximum"], 3), "degrees")
    print("Mean slope:", round(slope_stats["mean"], 3), "degrees")
    print("Median slope:", round(slope_stats["median"], 3), "degrees")
    print("75th percentile:", round(slope_stats["percentile_75"], 3), "degrees")
    print("90th percentile:", round(slope_stats["percentile_90"], 3), "degrees")
    print("95th percentile:", round(slope_stats["percentile_95"], 3), "degrees")

    print("\n========================================")
    print("       TERRAIN PROCESSING COMPLETE")
    print("========================================")