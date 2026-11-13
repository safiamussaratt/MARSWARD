
import json
from pathlib import Path

import numpy as np

from backend.terrain_processor import analyze_jezero
from backend.hazard_analyzer import analyze_hazards


def main():

    print("\n========================================")
    print("       MARSWARD TERRAIN ANALYSIS")
    print("========================================")

    # Run real NASA elevation and slope analysis.
    results = analyze_jezero()

    region = results["region"]
    slope = results["slope"]

    # Classify terrain using slope thresholds.
    hazards, hazard_summary = analyze_hazards(slope)

    # Create output directory.
    project_root = Path(__file__).resolve().parent.parent

    output_dir = project_root / "results" / "terrain"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Save extracted elevation raster.
    np.save(
        output_dir / "jezero_elevation.npy",
        region["elevation"]
    )

    # Save calculated slope raster.
    np.save(
        output_dir / "jezero_slope.npy",
        slope
    )

    # Save terrain hazard classification.
    np.save(
        output_dir / "jezero_hazard_classes.npy",
        hazards
    )

    # Prepare a summary report.
    report = {
        "dataset": "NASA MGS MOLA MEGDR",
        "region": region["bounds"],
        "raster_shape": list(region["elevation"].shape),
        "elevation_statistics": results["elevation_statistics"],
        "slope_statistics": results["slope_statistics"],
        "hazard_summary": hazard_summary,
        "classification_thresholds_degrees": {
            "gentle_max": 5,
            "moderate_max": 15,
            "steep_max": 25
        },
        "classification_note": (
            "Prototype slope categories. "
            "Thresholds are not validated astronaut "
            "or rover safety limits."
        )
    }

    with open(
        output_dir / "terrain_report.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(report, file, indent=4)

    print("\n========== HAZARD SUMMARY ==========")

    print("Total pixels:", hazard_summary["total_pixels"])

    for label, values in hazard_summary["categories"].items():

        print(
            f"{label}: {values['count']} pixels "
            f"({values['percentage']}%)"
        )

    print("\n========== SAVED OUTPUTS ===========")

    print("Output directory:", output_dir)

    print(" - jezero_elevation.npy")
    print(" - jezero_slope.npy")
    print(" - jezero_hazard_classes.npy")
    print(" - terrain_report.json")

    print("\n========================================")
    print("       ANALYSIS COMPLETED")
    print("========================================")


if __name__ == "__main__":
    main()
