
import struct
import zlib
import binascii

import numpy as np

from backend.terrain_processor import analyze_jezero
from backend.hazard_analyzer import (
    analyze_hazards,
    HAZARD_LABELS,
    GENTLE_MAX,
    MODERATE_MAX,
    STEEP_MAX
)


# The terrain analysis is cached after its first execution.
_TERRAIN_CACHE = None


# RGBA colours for the hazard overlay.
# Alpha controls transparency.
HAZARD_COLORS = {
    0: (46, 204, 113, 55),    # Gentle: green
    1: (241, 196, 15, 105),   # Moderate: yellow
    2: (230, 126, 34, 145),   # Steep: orange
    3: (231, 76, 60, 175),    # Very steep: red
    255: (0, 0, 0, 0)         # Unknown: transparent
}


def get_terrain_data():
    """
    Load and cache the Jezero terrain analysis.

    The MOLA dataset and slope calculations are processed
    only once during the lifetime of this Flask process.
    """

    global _TERRAIN_CACHE

    if _TERRAIN_CACHE is None:

        print("\n===================================")
        print("MARSWARD: INITIALIZING TERRAIN DATA")
        print("===================================")

        results = analyze_jezero()

        hazards, hazard_summary = analyze_hazards(
            results["slope"]
        )

        _TERRAIN_CACHE = {
            "region": results["region"],
            "slope": results["slope"],
            "elevation_statistics": results["elevation_statistics"],
            "slope_statistics": results["slope_statistics"],
            "hazards": hazards,
            "hazard_summary": hazard_summary
        }

        print("Terrain analysis cached successfully.")

    return _TERRAIN_CACHE


def get_terrain_summary():
    """
    Return terrain statistics in a JSON-compatible format.
    """

    data = get_terrain_data()

    region = data["region"]
    bounds = region["bounds"]

    elevation_stats = data["elevation_statistics"]
    slope_stats = data["slope_statistics"]

    return {
        "status": "success",
        "source": "NASA MOLA MEGDR",
        "region": {
            "name": "Jezero Crater",
            "bounds": bounds,
            "raster_rows": int(region["elevation"].shape[0]),
            "raster_columns": int(region["elevation"].shape[1])
        },
        "elevation": {
            "minimum": elevation_stats["minimum"],
            "maximum": elevation_stats["maximum"],
            "mean": elevation_stats["mean"],
            "median": elevation_stats["median"],
            "unit": "metres"
        },
        "slope": {
            "minimum": slope_stats["minimum"],
            "maximum": slope_stats["maximum"],
            "mean": slope_stats["mean"],
            "median": slope_stats["median"],
            "percentile_75": slope_stats["percentile_75"],
            "percentile_90": slope_stats["percentile_90"],
            "percentile_95": slope_stats["percentile_95"],
            "unit": "degrees"
        },
        "hazards": {
            "summary": data["hazard_summary"],
            "thresholds": {
                "gentle_max_degrees": GENTLE_MAX,
                "moderate_max_degrees": MODERATE_MAX,
                "steep_max_degrees": STEEP_MAX
            },
            "labels": HAZARD_LABELS
        }
    }


def inspect_terrain(longitude, latitude):
    """
    Find the nearest MOLA raster pixel to a map coordinate.
    Return its elevation, slope and hazard classification.
    """

    data = get_terrain_data()

    region = data["region"]
    bounds = region["bounds"]

    if not (
        bounds["west"] <= longitude <= bounds["east"]
        and bounds["south"] <= latitude <= bounds["north"]
    ):
        raise ValueError(
            "Selected coordinates are outside the Jezero analysis region."
        )

    # Find the nearest pixel centre.
    column = int(
        np.argmin(
            np.abs(region["longitudes"] - longitude)
        )
    )

    row = int(
        np.argmin(
            np.abs(region["latitudes"] - latitude)
        )
    )

    elevation = float(
        region["elevation"][row, column]
    )

    slope = float(
        data["slope"][row, column]
    )

    hazard_code = int(
        data["hazards"][row, column]
    )

    hazard_label = HAZARD_LABELS.get(
        hazard_code,
        "Unknown"
    )

    return {
        "status": "success",
        "requested_coordinates": {
            "longitude": float(longitude),
            "latitude": float(latitude)
        },
        "pixel_coordinates": {
            "longitude": float(region["longitudes"][column]),
            "latitude": float(region["latitudes"][row])
        },
        "raster_index": {
            "row": row,
            "column": column
        },
        "terrain": {
            "elevation_metres": round(elevation, 2),
            "slope_degrees": round(slope, 3),
            "hazard_code": hazard_code,
            "hazard_class": hazard_label
        }
    }


def _png_chunk(chunk_type, data):
    """
    Construct one PNG chunk with its CRC checksum.
    """

    chunk = chunk_type + data

    return (
        struct.pack(">I", len(data))
        + chunk
        + struct.pack(
            ">I",
            binascii.crc32(chunk) & 0xffffffff
        )
    )


def create_hazard_png():
    """
    Convert the hazard classification raster into
    a transparent RGBA PNG image.
    """

    data = get_terrain_data()
    hazards = data["hazards"]

    height, width = hazards.shape

    # Convert hazard codes into RGBA pixels.
    rgba = np.zeros(
        (height, width, 4),
        dtype=np.uint8
    )

    for code, color in HAZARD_COLORS.items():
        rgba[hazards == code] = color

    # PNG scanlines require a filter byte at the
    # beginning of each row. Filter 0 means no filter.
    raw_data = b"".join(
        b"\x00" + rgba[row].tobytes()
        for row in range(height)
    )

    compressed = zlib.compress(raw_data)

    # PNG header.
    png_signature = b"\x89PNG\r\n\x1a\n"

    # Image header: 8-bit RGBA, standard compression/filter.
    ihdr = struct.pack(
        ">2I5B",
        width,
        height,
        8,
        6,
        0,
        0,
        0
    )

    png_data = (
        png_signature
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )

    return png_data
