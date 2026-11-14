"""
MARSWARD EVA planner.

Turns a calculated route into a GO / CAUTION / NO-GO verdict
for one trip outside, with the reasons behind it.

The verdict uses:
- travel time along the route, slowed on sloping ground
- time spent at the destination
- the time limit for being outside, and a time reserve
- the steepest slope on the route
- dust and air temperature entered by the user

Every threshold here is a prototype planning assumption, not a
validated astronaut or rover safety limit.
"""

import math

from backend.mars_data import pixel_size_meters

from backend.route_optimizer import (
    haversine_distance_km,
    DEFAULT_MAX_SLOPE_DEGREES
)


MODES = {
    "foot": {"label": "On foot", "speed_kmh": 3.0},
    "rover": {"label": "Crew rover", "speed_kmh": 10.0}
}

DEFAULTS = {
    "travel_mode": "foot",
    "speed_kmh": 3.0,
    "time_limit_hours": 8.0,
    "time_at_site_hours": 1.0,
    "reserve_hours": 1.0,
    "round_trip": True,
    "max_slope_degrees": DEFAULT_MAX_SLOPE_DEGREES,
    "dust_opacity": 0.4,
    "air_temperature_c": -55.0
}

# (minimum, maximum) for each numeric setting.
LIMITS = {
    "speed_kmh": (0.1, 50.0),
    "time_limit_hours": (0.5, 48.0),
    "time_at_site_hours": (0.0, 48.0),
    "reserve_hours": (0.0, 24.0),
    "max_slope_degrees": (1.0, 90.0),
    "dust_opacity": (0.0, 10.0),
    "air_temperature_c": (-150.0, 40.0)
}

LABELS = {
    "speed_kmh": "Speed",
    "time_limit_hours": "Time limit",
    "time_at_site_hours": "Time at destination",
    "reserve_hours": "Time reserve",
    "max_slope_degrees": "Slope limit",
    "dust_opacity": "Dust opacity",
    "air_temperature_c": "Air temperature"
}

# Dust thresholds are anchored to what Perseverance measured
# in the January 2022 regional dust storm at Jezero: optical
# depth rose from about 0.3 to 0.8 as the storm arrived, and
# peaked near 2, when visibility across the crater was reduced
# (Lemmon et al., Geophysical Research Letters, 2022).
# Using those levels as caution and no-go limits is a MARSWARD
# planning choice, not a mission rule.
DUST_CAUTION = 0.8
DUST_NO_GO = 2.0
TEMPERATURE_CAUTION_C = -90.0
STEEP_CAUTION_DEGREES = 15.0

STATUS_GO = "GO"
STATUS_CAUTION = "CAUTION"
STATUS_NO_GO = "NO_GO"


def parse_settings(data):
    """
    Validate EVA settings, filling gaps with defaults.

    Raises ValueError for invalid values.
    """

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ValueError("EVA settings must be an object.")

    settings = dict(DEFAULTS)

    mode = data.get("travel_mode", DEFAULTS["travel_mode"])

    if mode not in MODES:
        raise ValueError("Travel mode must be 'foot' or 'rover'.")

    settings["travel_mode"] = mode
    settings["speed_kmh"] = MODES[mode]["speed_kmh"]

    for key, (low, high) in LIMITS.items():

        value = data.get(key)

        if value is None:
            continue

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{LABELS[key]} must be a number.")

        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(
                f"{LABELS[key]} must be between {low:g} and {high:g}."
            )

        settings[key] = float(value)

    round_trip = data.get("round_trip", DEFAULTS["round_trip"])

    if not isinstance(round_trip, bool):
        raise ValueError("Round trip must be true or false.")

    settings["round_trip"] = round_trip

    return settings


def format_duration(hours):
    """
    Format a duration in hours as '2 h 10 min'.
    """

    minutes = int(round(abs(hours) * 60))
    whole_hours, remainder = divmod(minutes, 60)

    if whole_hours and remainder:
        return f"{whole_hours} h {remainder} min"

    if whole_hours:
        return f"{whole_hours} h"

    return f"{remainder} min"


def speed_factor(grade):
    """
    Fraction of flat-ground speed kept on a given grade.

    Shape taken from Tobler's hiking function,
    speed ∝ exp(-3.5 * |grade + 0.05|), scaled so flat ground
    is 1.0 and capped there. It is an Earth walking model
    used here as a stand-in.
    """

    factor = (
        math.exp(-3.5 * abs(grade + 0.05))
        / math.exp(-3.5 * 0.05)
    )

    return min(1.0, factor)


def travel_hours(path, elevations, speed_kmh):
    """
    Travel time along a path of [longitude, latitude] points.
    """

    hours = 0.0

    for index in range(len(path) - 1):

        lon1, lat1 = path[index]
        lon2, lat2 = path[index + 1]

        distance_km = haversine_distance_km(lon1, lat1, lon2, lat2)

        if distance_km <= 0:
            continue

        rise_m = elevations[index + 1] - elevations[index]
        grade = rise_m / (distance_km * 1000.0)

        hours += distance_km / (speed_kmh * speed_factor(grade))

    return hours


def assess_eva(route, settings, no_route_reason=None):
    """
    Build the verdict.

    route: result of calculate_route, or None when no route
           exists within the slope limit.
    settings: result of parse_settings.
    """

    reasons = []

    def add(level, message):
        reasons.append({"level": level, "message": message})

    timing = None
    terrain = None

    limit = settings["time_limit_hours"]
    reserve = settings["reserve_hours"]
    slope_limit = settings["max_slope_degrees"]

    # ---------------- Route, time and slope ----------------

    if route is None:

        add(
            "critical",
            no_route_reason or "No route could be calculated."
        )

    else:

        path = route["path"]
        elevations = route["elevations_m"]
        speed = settings["speed_kmh"]

        outbound = travel_hours(path, elevations, speed)

        inbound = (
            travel_hours(path[::-1], elevations[::-1], speed)
            if settings["round_trip"]
            else 0.0
        )

        at_site = settings["time_at_site_hours"]
        total = outbound + inbound + at_site
        spare = limit - total

        one_way_km = route["distance_km"]

        timing = {
            "outbound_hours": round(outbound, 2),
            "return_hours": round(inbound, 2),
            "time_at_site_hours": round(at_site, 2),
            "total_hours": round(total, 2),
            "time_limit_hours": round(limit, 2),
            "spare_hours": round(spare, 2),
            "reserve_hours": round(reserve, 2),
            "total_text": format_duration(total),
            "spare_text": format_duration(spare)
        }

        steepest = route["max_slope_on_route_degrees"]

        terrain = {
            "one_way_distance_km": one_way_km,
            "total_distance_km": round(
                one_way_km * (2 if settings["round_trip"] else 1), 3
            ),
            "steepest_slope_degrees": steepest,
            "mean_slope_degrees": route["mean_slope_on_route_degrees"],
            "ascent_m": route["ascent_m"],
            "descent_m": route["descent_m"]
        }

        if spare < 0:
            add(
                "critical",
                f"The trip takes {format_duration(total)}, "
                f"{format_duration(spare)} over the "
                f"{format_duration(limit)} limit."
            )

        elif spare < reserve:
            add(
                "caution",
                f"Only {format_duration(spare)} to spare, less than "
                f"the {format_duration(reserve)} reserve."
            )

        else:
            add(
                "ok",
                f"The trip takes {format_duration(total)} of the "
                f"{format_duration(limit)} limit."
            )

        if steepest > STEEP_CAUTION_DEGREES:
            add(
                "caution",
                f"The route crosses steep ground: {steepest:.1f}° "
                f"at its steepest (limit {slope_limit:g}°)."
            )

        else:
            add(
                "ok",
                f"Steepest slope on the route is {steepest:.1f}°, "
                f"within the {slope_limit:g}° limit."
            )

    # ---------------- Dust and temperature ----------------

    dust = settings["dust_opacity"]
    temperature = settings["air_temperature_c"]

    if dust >= DUST_NO_GO:
        add(
            "critical",
            f"Dust opacity {dust:g} is at or above {DUST_NO_GO:g}, "
            f"the level of the January 2022 storm peak."
        )

    elif dust > DUST_CAUTION:
        add(
            "caution",
            f"Dust opacity {dust:g} is above {DUST_CAUTION:g}, "
            f"the level seen as the January 2022 storm arrived."
        )

    else:
        add("ok", f"Dust opacity {dust:g} is within limits.")

    if temperature < TEMPERATURE_CAUTION_C:
        add(
            "caution",
            f"Air temperature {temperature:g} °C is below the "
            f"{TEMPERATURE_CAUTION_C:g} °C caution threshold."
        )

    else:
        add("ok", f"Air temperature {temperature:g} °C is within limits.")

    # ---------------- Status and headline ----------------

    levels = {reason["level"] for reason in reasons}

    if "critical" in levels:
        status = STATUS_NO_GO
        first = next(r for r in reasons if r["level"] == "critical")
        headline = f"NO-GO: {first['message']}"

    elif "caution" in levels:
        status = STATUS_CAUTION
        first = next(r for r in reasons if r["level"] == "caution")
        headline = f"CAUTION: {first['message']}"

    else:
        status = STATUS_GO
        headline = (
            f"GO: {timing['spare_text']} to spare, steepest slope "
            f"{terrain['steepest_slope_degrees']:.1f}°."
        )

    # Most serious reasons first.
    order = {"critical": 0, "caution": 1, "ok": 2}
    reasons.sort(key=lambda reason: order[reason["level"]])

    return {
        "status": status,
        "headline": headline,
        "reasons": reasons,
        "timing": timing,
        "terrain": terrain,
        "conditions": {
            "dust_opacity": dust,
            "air_temperature_c": temperature
        },
        "settings": {
            **settings,
            "travel_mode_label": MODES[settings["travel_mode"]]["label"]
        },
        "assumptions": [
            "Speed drops on sloping ground using the shape of "
            "Tobler's hiking function, an Earth walking model.",
            f"Terrain pixels are about {pixel_size_meters():,.0f} m "
            "wide, so slopes are regional averages; boulders and "
            "scarps are not seen.",
            "Dust limits follow levels Perseverance measured in the "
            "January 2022 storm (Lemmon et al., 2022); using them "
            "as limits is a planning choice.",
            "Walking and rover speeds, the time limit, the slope "
            "limit and the cold threshold are assumptions you can "
            "edit, not validated safety limits."
        ]
    }