"""
MARSWARD Survival Simulator.

Estimates the water, food and oxygen a crew needs for a
surface mission, adds an emergency reserve, and compares the
result with the supplies on board.

Default consumption rates (kg per person per Earth day):

- Oxygen 0.84 and water 3.54: the widely quoted NASA crew
  metabolic balance (0.84 kg oxygen, 0.62 kg dry food and
  3.54 kg water in per day).
- Food 1.77: 1.51 kg edible food plus 0.26 kg packaging, as
  quoted from NASA's Life Support Baseline Values and
  Assumptions Document (NASA/TP-2015-218570 Rev 1).

These were taken from secondary sources quoting NASA; check
them against the NASA document before relying on them. They
are editable planning values, not mission requirements.
"""

import math


# One Martian sol = 88,775.244 s; one Earth day = 86,400 s.
SOL_IN_EARTH_DAYS = 88775.244 / 86400.0

RESOURCES = (
    ("water", "Water"),
    ("food", "Food"),
    ("oxygen", "Oxygen")
)

# Daily requirements are kilograms per person per Earth day.
DEFAULTS = {
    "crew_size": 4,
    "duration_sols": 30,
    "daily_per_person_kg": {
        "water": 3.54,    # drinking and food water, no hygiene water
        "food": 1.77,     # 1.51 edible + 0.26 packaging
        "oxygen": 0.84    # metabolic oxygen
    },
    "reserve_percent": 20,
    "supplies_kg": {
        "water": 520.0,
        "food": 250.0,
        "oxygen": 130.0
    }
}

LIMITS = {
    "crew_size": (1, 100),
    "duration_sols": (1, 2000),
    "daily_per_person_kg": (0.01, 50),
    "reserve_percent": (0, 100),
    "supplies_kg": (0, 10_000_000)
}

STATUS_SUFFICIENT = "SUFFICIENT"
STATUS_RESERVE_AT_RISK = "RESERVE_AT_RISK"
STATUS_INSUFFICIENT = "INSUFFICIENT"
STATUS_NOT_ASSESSED = "NOT_ASSESSED"

_STATUS_SEVERITY = {
    STATUS_NOT_ASSESSED: 0,
    STATUS_SUFFICIENT: 1,
    STATUS_RESERVE_AT_RISK: 2,
    STATUS_INSUFFICIENT: 3
}


def get_defaults():
    """
    Return default simulator inputs and their allowed ranges.
    """

    return {
        "status": "success",
        "defaults": DEFAULTS,
        "limits": {
            key: {"minimum": low, "maximum": high}
            for key, (low, high) in LIMITS.items()
        },
        "sol_in_earth_days": round(SOL_IN_EARTH_DAYS, 5)
    }


def _number(value, name, limit_key, integer=False):
    """
    Validate one numeric input and return it.
    """

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number.")

    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number.")

    if integer and value != int(value):
        raise ValueError(f"{name} must be a whole number.")

    low, high = LIMITS[limit_key]

    if not low <= value <= high:
        raise ValueError(
            f"{name} must be between {low} and {high}."
        )

    return int(value) if integer else float(value)


def _resource_values(data, key, name, limit_key, required=True):
    """
    Validate a {"water": ..., "food": ..., "oxygen": ...} block.
    """

    block = data.get(key)

    if block is None:
        if required:
            raise ValueError(f"Missing {name}.")
        return None

    if not isinstance(block, dict):
        raise ValueError(
            f"{name} must contain water, food and oxygen values."
        )

    return {
        resource: _number(
            block.get(resource),
            f"{label} ({name})",
            limit_key
        )
        for resource, label in RESOURCES
    }


def simulate_survival(data):
    """
    Run the survival calculation.

    Expected input:

        {
            "crew_size": 4,
            "duration_sols": 30,
            "daily_per_person_kg": {"water": .., "food": .., "oxygen": ..},
            "reserve_percent": 20,
            "supplies_kg": {"water": .., "food": .., "oxygen": ..}   # optional
        }

    Raises ValueError for invalid input.
    """

    if not isinstance(data, dict):
        raise ValueError("Missing survival simulation inputs.")

    crew_size = _number(
        data.get("crew_size"), "Crew size", "crew_size", integer=True
    )

    duration_sols = _number(
        data.get("duration_sols"), "Mission duration", "duration_sols"
    )

    reserve_percent = _number(
        data.get("reserve_percent"), "Emergency reserve", "reserve_percent"
    )

    daily = _resource_values(
        data, "daily_per_person_kg", "daily requirement",
        "daily_per_person_kg"
    )

    supplies = _resource_values(
        data, "supplies_kg", "supplies on board",
        "supplies_kg", required=False
    )

    duration_earth_days = duration_sols * SOL_IN_EARTH_DAYS
    person_days = crew_size * duration_earth_days

    resources = {}
    warnings = []

    for resource, label in RESOURCES:

        daily_crew = daily[resource] * crew_size
        per_sol_crew = daily_crew * SOL_IN_EARTH_DAYS

        base = daily_crew * duration_earth_days
        reserve = base * reserve_percent / 100.0
        total = base + reserve

        entry = {
            "label": label,
            "daily_per_person_kg": round(daily[resource], 3),
            "daily_crew_kg": round(daily_crew, 2),
            "base_requirement_kg": round(base, 2),
            "reserve_kg": round(reserve, 2),
            "total_required_kg": round(total, 2),
            "available_kg": None,
            "margin_kg": None,
            "sols_supported": None,
            "status": STATUS_NOT_ASSESSED
        }

        if supplies is not None:

            available = supplies[resource]
            sols_supported = available / per_sol_crew

            entry["available_kg"] = round(available, 2)
            entry["margin_kg"] = round(available - total, 2)
            entry["sols_supported"] = round(sols_supported, 1)

            if available < base:

                entry["status"] = STATUS_INSUFFICIENT

                warnings.append({
                    "level": "critical",
                    "resource": resource,
                    "message": (
                        f"{label} runs out during sol "
                        f"{int(sols_supported) + 1} of "
                        f"{duration_sols:g}. Short by "
                        f"{base - available:,.1f} kg for the "
                        f"planned mission."
                    )
                })

            elif available < total:

                entry["status"] = STATUS_RESERVE_AT_RISK

                covered = (available - base) / reserve * 100.0

                warnings.append({
                    "level": "warning",
                    "resource": resource,
                    "message": (
                        f"{label} covers the mission but only "
                        f"{covered:.0f}% of the emergency reserve "
                        f"({total - available:,.1f} kg below the "
                        f"reserve target)."
                    )
                })

            else:
                entry["status"] = STATUS_SUFFICIENT

        resources[resource] = entry

    if reserve_percent == 0:
        warnings.append({
            "level": "warning",
            "resource": None,
            "message": (
                "No emergency reserve is planned. Any delay or "
                "loss of supplies would leave the crew without margin."
            )
        })

    overall_status = max(
        (entry["status"] for entry in resources.values()),
        key=_STATUS_SEVERITY.get
    )

    limiting = None
    sols_supported = None

    if supplies is not None:

        limiting = min(
            resources,
            key=lambda name: resources[name]["sols_supported"]
        )

        sols_supported = resources[limiting]["sols_supported"]

    messages = {
        STATUS_SUFFICIENT: (
            "Supplies cover the mission and the full emergency reserve."
        ),
        STATUS_RESERVE_AT_RISK: (
            "Supplies cover the mission, but the emergency "
            "reserve is not fully stocked."
        ),
        STATUS_INSUFFICIENT: (
            "Supplies do not last the planned mission duration."
        ),
        STATUS_NOT_ASSESSED: (
            "Requirements calculated. Enter supplies on board "
            "to assess sufficiency."
        )
    }

    return {
        "status": "success",
        "mission": {
            "crew_size": crew_size,
            "duration_sols": round(duration_sols, 2),
            "duration_earth_days": round(duration_earth_days, 2),
            "person_days": round(person_days, 1),
            "reserve_percent": round(reserve_percent, 2)
        },
        "resources": resources,
        "overall": {
            "status": overall_status,
            "message": messages[overall_status],
            "limiting_resource": limiting,
            "limiting_resource_label": (
                resources[limiting]["label"] if limiting else None
            ),
            "sols_supported": sols_supported
        },
        "warnings": warnings,
        "assumptions": [
            "Requirements are per person per Earth day; one sol "
            f"is {SOL_IN_EARTH_DAYS:.4f} Earth days.",
            "Consumption is constant. No water or oxygen recycling, "
            "in-situ resource production or EVA overhead is modelled.",
            "Default rates: 0.84 kg oxygen and 3.54 kg water from "
            "NASA's crew metabolic balance; 1.77 kg food (1.51 kg "
            "edible plus 0.26 kg packaging) from NASA's Life Support "
            "Baseline Values and Assumptions Document. They are "
            "planning values you can edit, not mission requirements."
        ]
    }


if __name__ == "__main__":

    import json

    print(json.dumps(simulate_survival(DEFAULTS), indent=2))