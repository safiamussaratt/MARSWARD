
import numpy as np

# Prototype slope thresholds in degrees.
# These are configurable assumptions, not validated
# operational safety limits.

GENTLE_MAX = 5.0
MODERATE_MAX = 15.0
STEEP_MAX = 25.0

HAZARD_LABELS = {
    0: "Gentle",
    1: "Moderate",
    2: "Steep",
    3: "Very Steep"
}


def classify_slope(
    slope,
    gentle_max=GENTLE_MAX,
    moderate_max=MODERATE_MAX,
    steep_max=STEEP_MAX
):
    """
    Classify terrain according to slope angle.

    Returns a uint8 raster:
        0 = Gentle
        1 = Moderate
        2 = Steep
        3 = Very Steep
        255 = Invalid / unknown
    """

    slope = np.asarray(slope, dtype=np.float32)

    if slope.ndim != 2 or slope.size == 0:
        raise ValueError("Slope must be a non-empty 2D array.")

    if not (
        0 < gentle_max < moderate_max < steep_max <= 90
    ):
        raise ValueError("Invalid slope classification thresholds.")

    valid = np.isfinite(slope) & (slope >= 0) & (slope <= 90)

    hazards = np.full(slope.shape, 255, dtype=np.uint8)

    hazards[valid & (slope <= gentle_max)] = 0

    hazards[
        valid &
        (slope > gentle_max) &
        (slope <= moderate_max)
    ] = 1

    hazards[
        valid &
        (slope > moderate_max) &
        (slope <= steep_max)
    ] = 2

    hazards[
        valid &
        (slope > steep_max)
    ] = 3

    return hazards


def summarize_hazards(hazards):
    """
    Calculate the number and percentage of pixels
    belonging to each slope category.
    """

    hazards = np.asarray(hazards)

    if hazards.ndim != 2 or hazards.size == 0:
        raise ValueError("Invalid hazard raster.")

    valid = hazards != 255
    valid_count = int(np.count_nonzero(valid))

    results = {
        "total_pixels": int(hazards.size),
        "valid_pixels": valid_count,
        "unknown_pixels": int(hazards.size - valid_count),
        "categories": {}
    }

    for code, label in HAZARD_LABELS.items():

        count = int(np.count_nonzero(hazards == code))

        percentage = (
            (count / valid_count) * 100
            if valid_count > 0
            else 0.0
        )

        results["categories"][label] = {
            "count": count,
            "percentage": round(percentage, 2)
        }

    return results


def analyze_hazards(slope):
    """
    Classify slope raster and return its summary.
    """

    hazards = classify_slope(slope)

    summary = summarize_hazards(hazards)

    return hazards, summary


if __name__ == "__main__":

    from backend.terrain_processor import analyze_jezero

    print("\n========================================")
    print("       MARSWARD HAZARD ANALYZER")
    print("========================================")

    results = analyze_jezero()

    hazards, summary = analyze_hazards(results["slope"])

    print("\n========== TERRAIN CLASSIFICATION =====")

    print("Total pixels:", summary["total_pixels"])
    print("Valid pixels:", summary["valid_pixels"])
    print("Unknown pixels:", summary["unknown_pixels"])

    for label, values in summary["categories"].items():

        print(
            f"{label}: "
            f"{values['count']} pixels "
            f"({values['percentage']}%)"
        )

    print("\n========================================")
    print("       HAZARD ANALYSIS COMPLETE")
    print("========================================")
