"""
Build the small region file from the full NASA MOLA tile.

Run once, from the project root, on a machine that has
data/terrain/megt90n000gb.img:

    python -m backend.build_region_crop

It writes data/terrain/jezero_region.npz (about 150 KB), which
is committed to the repository so the app runs without the
133 MB tile.
"""

import os

from backend.mars_data import (
    load_mola_data,
    extract_region,
    save_region_file,
    load_region_file,
    JEZERO_BOUNDS,
    REGION_PATH
)


def main():

    region = extract_region(
        load_mola_data(),
        west_lon=JEZERO_BOUNDS["west"],
        east_lon=JEZERO_BOUNDS["east"],
        south_lat=JEZERO_BOUNDS["south"],
        north_lat=JEZERO_BOUNDS["north"]
    )

    save_region_file(region, REGION_PATH)

    check = load_region_file(REGION_PATH)

    if not (check["elevation"] == region["elevation"]).all():
        raise RuntimeError("Saved region does not match the source.")

    print("Saved:", REGION_PATH)
    print("Raster:", check["elevation"].shape)
    print("Size:", os.path.getsize(REGION_PATH), "bytes")


if __name__ == "__main__":
    main()