
import math
import heapq


GRID_SIZE = 40

# Simulated terrain for initial algorithm testing.
# These values are NOT actual NASA elevation measurements.

def generate_terrain():
    terrain = []

    for y in range(GRID_SIZE):
        row = []

        for x in range(GRID_SIZE):

            elevation = (
                100 * math.sin(x / 5)
                + 80 * math.cos(y / 6)
                + 40 * math.sin((x + y) / 4)
            )

            roughness = abs(
                math.sin(x * 0.7) * math.cos(y * 0.4)
            )

            # Simulated hazard zones
            hazard = 0

            if 12 <= x <= 19 and 10 <= y <= 17:
                hazard = 8

            if 26 <= x <= 31 and 23 <= y <= 29:
                hazard = 5

            row.append({
                "elevation": elevation,
                "roughness": roughness,
                "hazard": hazard
            })

        terrain.append(row)

    return terrain


TERRAIN = generate_terrain()


def heuristic(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]

    return math.sqrt(dx * dx + dy * dy)


def terrain_cost(current, neighbor):

    x1, y1 = current
    x2, y2 = neighbor

    current_cell = TERRAIN[y1][x1]
    next_cell = TERRAIN[y2][x2]

    elevation_difference = abs(
        current_cell["elevation"] -
        next_cell["elevation"]
    )

    roughness = next_cell["roughness"]
    hazard = next_cell["hazard"]

    slope_penalty = elevation_difference * 0.08

    distance = heuristic(current, neighbor)

    cost = distance * (
        1
        + slope_penalty
        + roughness * 2
        + hazard
    )

    return cost


def get_neighbors(node):

    x, y = node

    directions = [
        (0, 1), (0, -1),
        (1, 0), (-1, 0),
        (1, 1), (1, -1),
        (-1, 1), (-1, -1)
    ]

    neighbors = []

    for dx, dy in directions:

        nx = x + dx
        ny = y + dy

        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
            neighbors.append((nx, ny))

    return neighbors


def find_path(start, goal):

    open_set = []

    heapq.heappush(
        open_set,
        (0, start)
    )

    came_from = {}

    g_score = {
        start: 0
    }

    visited = set()

    while open_set:

        _, current = heapq.heappop(open_set)

        if current in visited:
            continue

        visited.add(current)

        if current == goal:

            path = [current]

            while current in came_from:
                current = came_from[current]
                path.append(current)

            path.reverse()

            return {
                "path": path,
                "cost": g_score[goal],
                "visited": len(visited)
            }

        for neighbor in get_neighbors(current):

            if neighbor in visited:
                continue

            tentative_score = (
                g_score[current]
                + terrain_cost(current, neighbor)
            )

            if tentative_score < g_score.get(
                neighbor, float("inf")
            ):

                came_from[neighbor] = current

                g_score[neighbor] = tentative_score

                f_score = (
                    tentative_score
                    + heuristic(neighbor, goal)
                )

                heapq.heappush(
                    open_set,
                    (f_score, neighbor)
                )

    return None


def calculate_route(start, destination):

    start_lon, start_lat = start
    end_lon, end_lat = destination

    # Initial demonstration region around Jezero.
    min_lon, max_lon = 74.0, 81.0
    min_lat, max_lat = 16.0, 21.0

    coordinates = [
        start_lon, start_lat,
        end_lon, end_lat
    ]

    if not all(math.isfinite(v) for v in coordinates):
        raise ValueError("Coordinates must be finite numbers.")

    if not (
        min_lon <= start_lon <= max_lon
        and min_lon <= end_lon <= max_lon
        and min_lat <= start_lat <= max_lat
        and min_lat <= end_lat <= max_lat
    ):
        raise ValueError(
            "Both locations must be inside the Jezero demonstration region."
        )

    def to_grid(lon, lat):

        x = round(
            (lon - min_lon)
            / (max_lon - min_lon)
            * (GRID_SIZE - 1)
        )

        y = round(
            (lat - min_lat)
            / (max_lat - min_lat)
            * (GRID_SIZE - 1)
        )

        return x, y

    def to_coordinates(x, y):

        lon = min_lon + (
            x / (GRID_SIZE - 1)
        ) * (max_lon - min_lon)

        lat = min_lat + (
            y / (GRID_SIZE - 1)
        ) * (max_lat - min_lat)

        return [lon, lat]

    start_grid = to_grid(start_lon, start_lat)
    goal_grid = to_grid(end_lon, end_lat)

    result = find_path(start_grid, goal_grid)

    if result is None:
        raise ValueError("No route could be calculated.")

    path_coordinates = [
        to_coordinates(x, y)
        for x, y in result["path"]
    ]

    total_distance = sum(
        heuristic(a, b)
        for a, b in zip(
            result["path"],
            result["path"][1:]
        )
    )

    return {
        "path": path_coordinates,
        "distance_grid_units": round(total_distance, 2),
        "terrain_cost": round(result["cost"], 2),
        "visited_nodes": result["visited"],
        "model": "SIMULATED TERRAIN",
        "grid_size": GRID_SIZE
    }
