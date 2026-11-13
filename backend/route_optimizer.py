
import math
import heapq
import numpy as np

from backend.mars_data import (
    load_mola_data,
    extract_region,
    coordinates_to_pixel,
    pixel_to_coordinates,
    JEZERO_BOUNDS,
    MARS_RADIUS_KM
)

from backend.terrain_processor import calculate_slope


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

MIN_LON = JEZERO_BOUNDS["west"]
MAX_LON = JEZERO_BOUNDS["east"]

MIN_LAT = JEZERO_BOUNDS["south"]
MAX_LAT = JEZERO_BOUNDS["north"]

# A* uses the actual 320 x 448 MOLA Jezero raster.
# No simulated terrain is generated.

MOVEMENT_DIRECTIONS = [
    (0, 1),
    (0, -1),
    (1, 0),
    (-1, 0),
    (1, 1),
    (1, -1),
    (-1, 1),
    (-1, -1)
]

# Terrain penalty settings.
# These are illustrative route-planning weights,
# not validated rover safety thresholds.

SLOPE_WEIGHT = 0.035
STEEP_SLOPE_WEIGHT = 0.003
ELEVATION_WEIGHT = 0.05


# --------------------------------------------------
# TERRAIN CACHE
# --------------------------------------------------

_TERRAIN_CACHE = None


def get_terrain():
    """
    Load and cache actual NASA MOLA terrain.

    The dataset and slope raster are loaded only once
    per Python process.
    """

    global _TERRAIN_CACHE

    if _TERRAIN_CACHE is not None:
        return _TERRAIN_CACHE

    print("\n[A*] Loading NASA MOLA terrain...")

    mola_data = load_mola_data()

    region = extract_region(mola_data)

    print("[A*] Calculating actual terrain slope...")

    slope = calculate_slope(region)

    elevation = np.asarray(
        region["elevation"],
        dtype=np.float32
    )

    if elevation.shape != slope.shape:
        raise ValueError(
            "Elevation and slope raster dimensions do not match."
        )

    if elevation.size == 0:
        raise ValueError(
            "NASA MOLA terrain raster is empty."
        )

    if not np.all(np.isfinite(elevation)):
        raise ValueError(
            "Elevation raster contains invalid values."
        )

    if not np.all(np.isfinite(slope)):
        raise ValueError(
            "Slope raster contains invalid values."
        )

    _TERRAIN_CACHE = {
        "elevation": elevation,
        "slope": slope,
        "rows": elevation.shape[0],
        "columns": elevation.shape[1],
        "region": region
    }

    print(
        "[A*] Actual MOLA terrain ready:",
        elevation.shape
    )

    return _TERRAIN_CACHE


# --------------------------------------------------
# DISTANCE CALCULATION
# --------------------------------------------------

def haversine_distance_km(lon1, lat1, lon2, lat2):
    """
    Calculate surface distance between two coordinates
    using Mars' reference radius.

    Returns distance in kilometres.
    """

    lon1 = math.radians(lon1)
    lat1 = math.radians(lat1)

    lon2 = math.radians(lon2)
    lat2 = math.radians(lat2)

    delta_lon = lon2 - lon1
    delta_lat = lat2 - lat1

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    a = min(1.0, max(0.0, a))

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return MARS_RADIUS_KM * c


def heuristic(current, goal):
    """
    A* heuristic using straight-line surface distance.

    Terrain penalties are always non-negative, so this
    remains an admissible distance-based lower bound.
    """

    current_lon, current_lat = pixel_to_coordinates(
        current[0],
        current[1]
    )

    goal_lon, goal_lat = pixel_to_coordinates(
        goal[0],
        goal[1]
    )

    return haversine_distance_km(
        current_lon,
        current_lat,
        goal_lon,
        goal_lat
    )


# --------------------------------------------------
# NEIGHBOURS
# --------------------------------------------------

def get_neighbors(node, rows, columns):
    """
    Return valid 8-directional neighbouring pixels.
    """

    x, y = node

    neighbors = []

    for dx, dy in MOVEMENT_DIRECTIONS:

        nx = x + dx
        ny = y + dy

        if (
            0 <= nx < columns
            and 0 <= ny < rows
        ):
            neighbors.append((nx, ny))

    return neighbors


# --------------------------------------------------
# TERRAIN-AWARE COST
# --------------------------------------------------

def terrain_cost(current, neighbor, terrain):
    """
    Calculate movement cost using actual MOLA terrain.

    Factors:
    - Physical surface distance
    - Average slope of the two cells
    - Elevation difference between the cells

    Steeper terrain and larger elevation changes
    receive higher movement costs.
    """

    x1, y1 = current
    x2, y2 = neighbor

    elevation = terrain["elevation"]
    slope = terrain["slope"]

    current_elevation = float(
        elevation[y1, x1]
    )

    next_elevation = float(
        elevation[y2, x2]
    )

    current_slope = float(
        slope[y1, x1]
    )

    next_slope = float(
        slope[y2, x2]
    )

    average_slope = (
        current_slope + next_slope
    ) / 2.0

    elevation_difference = abs(
        next_elevation - current_elevation
    )

    current_lon, current_lat = pixel_to_coordinates(
        x1,
        y1
    )

    next_lon, next_lat = pixel_to_coordinates(
        x2,
        y2
    )

    distance = haversine_distance_km(
        current_lon,
        current_lat,
        next_lon,
        next_lat
    )

    # General slope penalty.
    slope_penalty = (
        average_slope * SLOPE_WEIGHT
    )

    # Additional penalty for slopes above 5 degrees.
    steep_slope_penalty = (
        max(0.0, average_slope - 5.0) ** 2
        * STEEP_SLOPE_WEIGHT
    )

    # Additional penalty for elevation changes.
    elevation_penalty = (
        elevation_difference / 1000.0
        * ELEVATION_WEIGHT
    )

    total_multiplier = (
        1.0
        + slope_penalty
        + steep_slope_penalty
        + elevation_penalty
    )

    return distance * total_multiplier


# --------------------------------------------------
# A* PATHFINDING
# --------------------------------------------------

def find_path(start, goal, terrain):
    """
    A* pathfinding over the actual NASA MOLA raster.

    Coordinates:
        start = (column, row)
        goal = (column, row)

    Returns:
        path
        cost
        visited
        distance_km
    """

    rows = terrain["rows"]
    columns = terrain["columns"]

    if not (
        0 <= start[0] < columns
        and 0 <= start[1] < rows
    ):
        raise ValueError(
            "Starting pixel is outside the terrain raster."
        )

    if not (
        0 <= goal[0] < columns
        and 0 <= goal[1] < rows
    ):
        raise ValueError(
            "Destination pixel is outside the terrain raster."
        )

    if start == goal:
        return {
            "path": [start],
            "cost": 0.0,
            "visited": 1,
            "distance_km": 0.0
        }

    total_cells = rows * columns

    # Convert 2D pixel coordinates into flat array indices.
    def to_index(x, y):
        return y * columns + x

    def to_pixel(index):
        return (
            index % columns,
            index // columns
        )

    start_index = to_index(
        start[0],
        start[1]
    )

    goal_index = to_index(
        goal[0],
        goal[1]
    )

    g_score = np.full(
        total_cells,
        np.inf,
        dtype=np.float64
    )

    came_from = np.full(
        total_cells,
        -1,
        dtype=np.int32
    )

    visited = np.zeros(
        total_cells,
        dtype=bool
    )

    g_score[start_index] = 0.0

    open_set = []

    heapq.heappush(
        open_set,
        (
            heuristic(start, goal),
            start_index
        )
    )

    visited_count = 0

    while open_set:

        _, current_index = heapq.heappop(
            open_set
        )

        if visited[current_index]:
            continue

        current = to_pixel(current_index)

        visited[current_index] = True
        visited_count += 1

        if current_index == goal_index:

            # Reconstruct the route.
            path = []

            index = goal_index

            while index != -1:

                path.append(
                    to_pixel(index)
                )

                if index == start_index:
                    break

                index = int(
                    came_from[index]
                )

            path.reverse()

            # Calculate actual physical route distance.
            distance_km = 0.0

            for first, second in zip(
                path,
                path[1:]
            ):

                lon1, lat1 = pixel_to_coordinates(
                    first[0],
                    first[1]
                )

                lon2, lat2 = pixel_to_coordinates(
                    second[0],
                    second[1]
                )

                distance_km += haversine_distance_km(
                    lon1,
                    lat1,
                    lon2,
                    lat2
                )

            return {
                "path": path,
                "cost": float(
                    g_score[goal_index]
                ),
                "visited": visited_count,
                "distance_km": distance_km
            }

        for neighbor in get_neighbors(
            current,
            rows,
            columns
        ):

            neighbor_index = to_index(
                neighbor[0],
                neighbor[1]
            )

            if visited[neighbor_index]:
                continue

            movement_cost = terrain_cost(
                current,
                neighbor,
                terrain
            )

            tentative_score = (
                g_score[current_index]
                + movement_cost
            )

            if tentative_score < g_score[neighbor_index]:

                came_from[neighbor_index] = (
                    current_index
                )

                g_score[neighbor_index] = (
                    tentative_score
                )

                estimated_total = (
                    tentative_score
                    + heuristic(neighbor, goal)
                )

                heapq.heappush(
                    open_set,
                    (
                        estimated_total,
                        neighbor_index
                    )
                )

    return None


# --------------------------------------------------
# MAIN ROUTE FUNCTION
# --------------------------------------------------

def calculate_route(start, destination):
    """
    Calculate a terrain-aware route between two
    longitude/latitude coordinates inside Jezero Crater.

    This function preserves the existing interface:

        calculate_route(start, destination)

    Both arguments must be:

        [longitude, latitude]

    The returned path also uses geographic coordinates.
    """

    if (
        not isinstance(start, (list, tuple))
        or len(start) != 2
    ):
        raise ValueError(
            "Start must contain [longitude, latitude]."
        )

    if (
        not isinstance(destination, (list, tuple))
        or len(destination) != 2
    ):
        raise ValueError(
            "Destination must contain [longitude, latitude]."
        )

    try:
        start_lon = float(start[0])
        start_lat = float(start[1])

        end_lon = float(destination[0])
        end_lat = float(destination[1])

    except (TypeError, ValueError):
        raise ValueError(
            "Coordinates must be valid numbers."
        )

    coordinates = [
        start_lon,
        start_lat,
        end_lon,
        end_lat
    ]

    if not all(
        math.isfinite(value)
        for value in coordinates
    ):
        raise ValueError(
            "Coordinates must be finite numbers."
        )

    if not (
        MIN_LON <= start_lon <= MAX_LON
        and MIN_LON <= end_lon <= MAX_LON
        and MIN_LAT <= start_lat <= MAX_LAT
        and MIN_LAT <= end_lat <= MAX_LAT
    ):
        raise ValueError(
            "Both locations must be inside the Jezero demonstration region."
        )

    print("\n[A*] Calculating route...")

    terrain = get_terrain()

    # Convert geographic coordinates to actual MOLA pixels.
    start_column, start_row = coordinates_to_pixel(
        start_lon,
        start_lat
    )

    goal_column, goal_row = coordinates_to_pixel(
        end_lon,
        end_lat
    )

    # Clamp edge coordinates to the raster dimensions.
    start_column = max(
        0,
        min(terrain["columns"] - 1, start_column)
    )

    start_row = max(
        0,
        min(terrain["rows"] - 1, start_row)
    )

    goal_column = max(
        0,
        min(terrain["columns"] - 1, goal_column)
    )

    goal_row = max(
        0,
        min(terrain["rows"] - 1, goal_row)
    )

    start_pixel = (
        start_column,
        start_row
    )

    goal_pixel = (
        goal_column,
        goal_row
    )

    print(
        "[A*] Start pixel:",
        start_pixel
    )

    print(
        "[A*] Destination pixel:",
        goal_pixel
    )

    result = find_path(
        start_pixel,
        goal_pixel,
        terrain
    )

    if result is None:
        raise ValueError(
            "No route could be calculated."
        )

    # Convert every raster pixel in the path to
    # its geographic pixel-centre coordinates.
    path_coordinates = [
        pixel_to_coordinates(x, y)
        for x, y in result["path"]
    ]

    # Retain the legacy grid-distance field for compatibility.
    distance_grid_units = sum(
        math.hypot(
            second[0] - first[0],
            second[1] - first[1]
        )
        for first, second in zip(
            result["path"],
            result["path"][1:]
        )
    )

    print(
        "[A*] Route calculated successfully."
    )

    print(
        "[A*] Route points:",
        len(path_coordinates)
    )

    print(
        "[A*] Visited nodes:",
        result["visited"]
    )

    print(
        "[A*] Physical distance:",
        round(result["distance_km"], 3),
        "km"
    )

    return {
        "path": path_coordinates,

        "distance_grid_units": round(
            distance_grid_units,
            2
        ),

        "distance_km": round(
            result["distance_km"],
            3
        ),

        "terrain_cost": round(
            result["cost"],
            3
        ),

        "visited_nodes": result["visited"],

        "model": "NASA MOLA ACTUAL TERRAIN - A*",

        "grid_size": (
            f'{terrain["rows"]} x {terrain["columns"]}'
        ),

        "grid_dimensions": [
            terrain["rows"],
            terrain["columns"]
        ],

        "terrain_source": "NASA MOLA MEGDR",

        "terrain_resolution": (
            "1/64 degree per pixel"
        ),

        "region": "Jezero Crater"
    }
