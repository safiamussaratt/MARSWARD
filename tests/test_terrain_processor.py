
import os
import unittest

import numpy as np

from backend.terrain_processor import (
    PIXEL_SIZE_METERS,
    calculate_slope,
    get_slope_statistics
)

from backend.hazard_analyzer import (
    classify_slope,
    summarize_hazards
)

from backend.mars_data import (
    DATA_PATH,
    load_mola_data,
    extract_region
)


class TestTerrainProcessor(unittest.TestCase):

    def make_region(self, elevation, latitudes=None):

        rows, columns = elevation.shape

        if latitudes is None:
            latitudes = np.linspace(20, 16, rows)

        longitudes = np.linspace(74, 81, columns)

        return {
            "elevation": elevation,
            "latitudes": latitudes,
            "longitudes": longitudes
        }

    def test_flat_terrain(self):

        elevation = np.zeros((10, 10))

        region = self.make_region(elevation)

        slope = calculate_slope(region)

        self.assertTrue(
            np.allclose(slope, 0, atol=0.001)
        )

    def test_east_west_slope(self):

        rows = 10
        columns = 10

        latitude = 18.0

        dx = (
            PIXEL_SIZE_METERS *
            np.cos(np.deg2rad(latitude))
        )

        gradient = 0.1

        row = (
            np.arange(columns) *
            dx *
            gradient
        )

        elevation = np.tile(row, (rows, 1))

        region = self.make_region(
            elevation,
            np.full(rows, latitude)
        )

        slope = calculate_slope(region)

        expected = np.degrees(
            np.arctan(gradient)
        )

        self.assertTrue(
            np.allclose(slope, expected, atol=0.01)
        )

    def test_north_south_slope(self):

        rows = 10
        columns = 10

        gradient = 0.2

        elevation = np.tile(
            np.arange(rows)[:, np.newaxis] *
            PIXEL_SIZE_METERS *
            gradient,
            (1, columns)
        )

        region = self.make_region(elevation)

        slope = calculate_slope(region)

        expected = np.degrees(
            np.arctan(gradient)
        )

        self.assertTrue(
            np.allclose(slope, expected, atol=0.01)
        )

    def test_slope_statistics(self):

        slope = np.array([
            [1, 2],
            [3, 4]
        ], dtype=np.float32)

        stats = get_slope_statistics(slope)

        self.assertEqual(stats["minimum"], 1)
        self.assertEqual(stats["maximum"], 4)
        self.assertEqual(stats["mean"], 2.5)
        self.assertEqual(stats["median"], 2.5)

    def test_invalid_region(self):

        region = {
            "elevation": np.ones((5, 5)),
            "latitudes": np.ones(4),
            "longitudes": np.ones(5)
        }

        with self.assertRaises(ValueError):
            calculate_slope(region)

    def test_hazard_classification(self):

        slope = np.array([
            [0, 5, 6],
            [15, 16, 25],
            [26, 40, 90]
        ], dtype=np.float32)

        hazards = classify_slope(slope)

        expected = np.array([
            [0, 0, 1],
            [1, 2, 2],
            [3, 3, 3]
        ], dtype=np.uint8)

        np.testing.assert_array_equal(
            hazards,
            expected
        )

    def test_unknown_slope(self):

        slope = np.array([
            [2, np.nan],
            [10, -1]
        ], dtype=np.float32)

        hazards = classify_slope(slope)

        expected = np.array([
            [0, 255],
            [1, 255]
        ], dtype=np.uint8)

        np.testing.assert_array_equal(
            hazards,
            expected
        )

    def test_hazard_summary(self):

        hazards = np.array([
            [0, 0, 1],
            [1, 2, 3]
        ], dtype=np.uint8)

        summary = summarize_hazards(hazards)

        self.assertEqual(summary["total_pixels"], 6)
        self.assertEqual(summary["valid_pixels"], 6)

        self.assertEqual(
            summary["categories"]["Gentle"]["count"],
            2
        )

        self.assertEqual(
            summary["categories"]["Moderate"]["count"],
            2
        )

        self.assertEqual(
            summary["categories"]["Steep"]["count"],
            1
        )

        self.assertEqual(
            summary["categories"]["Very Steep"]["count"],
            1
        )


@unittest.skipUnless(
    os.path.exists(DATA_PATH),
    "NASA MOLA dataset is not installed."
)
class TestRealMolaDataset(unittest.TestCase):

    def test_real_jezero_extraction_and_slope(self):

        elevation = load_mola_data()

        region = extract_region(elevation)

        self.assertEqual(
            region["elevation"].shape,
            (320, 448)
        )

        slope = calculate_slope(region)

        self.assertEqual(slope.shape, (320, 448))

        self.assertTrue(np.all(np.isfinite(slope)))

        self.assertTrue(np.all(slope >= 0))

        self.assertTrue(np.all(slope <= 90))

        hazards = classify_slope(slope)

        self.assertEqual(hazards.shape, (320, 448))


if __name__ == "__main__":
    unittest.main(verbosity=2)
