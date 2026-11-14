"""
MARSWARD Science Explorer.

Combines reference information about Mars, Jezero Crater and
the NASA MOLA dataset with the terrain statistics already
computed by terrain_service. No terrain calculation is
repeated here.
"""

from backend.mars_data import (
    get_region,
    pixel_size_meters,
    MARS_RADIUS_KM
)

from backend.terrain_service import get_terrain_summary
from backend.science_stops import get_science_stops, CONDITIONS


def _facts(*pairs):
    return [
        {"label": label, "value": value}
        for label, value in pairs
    ]


MARS_FACTS = _facts(
    ("Mean radius", "3,389.5 km (about half of Earth's)"),
    ("Surface gravity", "3.71 m/s² (38% of Earth's)"),
    ("Length of a sol", "24 h 39 min 35 s"),
    ("Length of a year", "687 Earth days (about 669 sols)"),
    ("Average distance from the Sun", "1.52 AU (228 million km)"),
    ("Atmosphere", "About 95% carbon dioxide"),
    ("Mean surface pressure", "About 6 mbar (under 1% of Earth's)"),
    ("Mean surface temperature", "About −63 °C")
)

JEZERO_FACTS = _facts(
    ("Crater centre", "18.38° N, 77.58° E"),
    ("Diameter", "About 45 km"),
    ("Setting", "Western edge of Isidis Planitia"),
    ("Why it matters",
     "Ancient lake basin with a preserved river delta"),
    ("Estimated age of the lake", "More than 3.5 billion years"),
    ("Mission", "NASA Mars 2020 Perseverance rover"),
    ("Landing date", "18 February 2021")
)


def _dataset_facts(region):

    dataset = region["dataset"]
    bounds = region["bounds"]
    rows, columns = region["elevation"].shape

    return _facts(
        ("Dataset", dataset["name"]),
        ("Instrument", dataset["instrument"]),
        ("Product", dataset["product"]),
        ("Source file", dataset["source_file"]),
        ("Format", dataset["format"]),
        ("Resolution",
         f"{region['pixels_per_degree']:g} pixels per degree "
         f"(about {pixel_size_meters(region):,.0f} m per pixel)"),
        ("Reference radius", f"{MARS_RADIUS_KM:,.0f} km"),
        ("MARSWARD study region",
         f"{bounds['west']:g}–{bounds['east']:g}° E, "
         f"{bounds['south']:g}–{bounds['north']:g}° N "
         f"({rows} × {columns} pixels)")
    )


def get_science_overview():
    """
    Return everything the Science Explorer view displays.

    Reference facts are always returned. If the MOLA dataset
    cannot be loaded, "terrain" is None and "terrain_error"
    explains why, so the page can still show the rest.
    """

    terrain = None
    terrain_error = None

    dataset = {"title": "Terrain Dataset", "facts": []}
    notes = []

    try:
        region = get_region()

        dataset = {
            "title": f"{region['dataset']['name']} Dataset",
            "facts": _dataset_facts(region)
        }

        notes.append(
            "Slopes are measured between neighbouring pixels about "
            f"{pixel_size_meters(region):,.0f} m apart. They describe "
            "regional relief; smaller hazards such as boulders and "
            "scarps are not resolved."
        )

        terrain = get_terrain_summary()

    except Exception as error:
        terrain_error = str(error) or "Terrain data unavailable."

    notes.append(
        "Hazard classes use prototype slope thresholds, not "
        "validated rover or astronaut safety limits."
    )

    return {
        "status": "success",
        "mars": {
            "title": "Mars",
            "facts": MARS_FACTS
        },
        "jezero": {
            "title": "Jezero Crater",
            "facts": JEZERO_FACTS
        },
        "dataset": dataset,
        "conditions": CONDITIONS,
        "stops": get_science_stops(),
        "terrain": terrain,
        "terrain_error": terrain_error,
        "notes": notes
    }