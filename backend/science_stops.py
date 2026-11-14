"""
MARSWARD science stops and surface conditions.

Named places in Jezero Crater that can be chosen as route
destinations, and reference surface conditions measured by
the Perseverance rover's MEDA weather station.

Position sources:
- Octavia E. Butler Landing: published landing coordinates.
- Jezero Basin Centre, Neretva Vallis, Pliva Vallis: feature
  centres from the IAU Gazetteer of Planetary Nomenclature.
  A valley's centre is the middle of the whole valley, which
  for Neretva and Pliva lies outside the crater rim.
- Three Forks and Western Delta Top: placed by eye from
  published mission maps and marked approximate.
"""

from backend.terrain_service import inspect_terrain


STOPS = [
    {
        "id": "landing",
        "name": "Octavia E. Butler Landing",
        "longitude": 77.4508,
        "latitude": 18.4447,
        "approximate": False,
        "summary": (
            "Where Perseverance touched down on 18 February 2021, "
            "on the crater floor about 2 km from the delta."
        ),
        "science": "Igneous crater-floor rocks sampled in the first campaign."
    },
    {
        "id": "three-forks",
        "name": "Three Forks",
        "longitude": 77.40,
        "latitude": 18.455,
        "approximate": True,
        "summary": (
            "Flat ground at the base of the delta where Perseverance "
            "laid out a depot of 10 sample tubes."
        ),
        "science": "First sample depot on another world; delta-front sediments."
    },
    {
        "id": "delta-top",
        "name": "Western Delta Top",
        "longitude": 77.37,
        "latitude": 18.48,
        "approximate": True,
        "summary": (
            "The upper surface of the fan-shaped delta built by a "
            "river that once flowed into the crater lake."
        ),
        "science": "River-laid sandstones and boulders washed in from outside Jezero."
    },
    {
        "id": "neretva-vallis",
        "name": "Neretva Vallis",
        "longitude": 77.20,
        "latitude": 18.55,
        "approximate": False,
        "summary": (
            "The ancient river valley west of the crater that cut "
            "through the rim and fed the delta."
        ),
        "science": "Inlet channel recording when and how water entered the lake."
    },
    {
        "id": "crater-centre",
        "name": "Jezero Basin Centre",
        "longitude": 77.58,
        "latitude": 18.38,
        "approximate": False,
        "summary": (
            "The centre of the 45 km crater, on the floor of the "
            "former lake."
        ),
        "science": "Deepest part of the lake basin."
    },
    {
        "id": "pliva-vallis",
        "name": "Pliva Vallis",
        "longitude": 78.35,
        "latitude": 18.67,
        "approximate": False,
        "summary": (
            "The outlet valley east of the crater, cut when the "
            "lake overflowed its rim."
        ),
        "science": "Evidence the lake filled until it breached the rim."
    }
]


CONDITIONS = {
    "title": "Surface Conditions at Jezero",
    "source": (
        "Perseverance MEDA weather station, first 250 sols "
        "(Rodríguez-Manfredi et al., Nature Geoscience, 2023); "
        "dust figures from Lemmon et al., Geophysical Research "
        "Letters, 2022"
    ),
    "source_url": "https://doi.org/10.1038/s41561-022-01084-0",
    "facts": [
        {
            "label": "Mean air temperature",
            "value": "About −55 °C"
        },
        {
            "label": "Day-to-night temperature swing",
            "value": "50 to 60 °C"
        },
        {
            "label": "Dust devils",
            "value": "Frequent; 5 to 135 m across where measured"
        },
        {
            "label": "Dust opacity before the January 2022 storm",
            "value": "About 0.3"
        },
        {
            "label": "Dust opacity as the storm arrived",
            "value": "About 0.8"
        },
        {
            "label": "Dust opacity at the storm peak",
            "value": "About 2, with reduced visibility across the crater"
        }
    ],
    "note": (
        "The route verdict uses the dust opacity and air "
        "temperature you enter. It warns above 0.8 and returns "
        "NO-GO at 2 or above, matching the storm levels listed "
        "here; the cold threshold (−90 °C) is an assumption."
    )
}


def get_science_stops():
    """
    Return the stops with MOLA terrain readings where available.
    """

    stops = []

    for stop in STOPS:

        entry = dict(stop)
        entry["terrain"] = None

        try:
            reading = inspect_terrain(
                stop["longitude"],
                stop["latitude"]
            )

            entry["terrain"] = reading["terrain"]

        except Exception:
            # Terrain data missing: the stop is still usable.
            pass

        stops.append(entry)

    return stops