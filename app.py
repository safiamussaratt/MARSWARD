from io import BytesIO

from flask import Flask, send_from_directory, send_file, jsonify, request

from backend.mars_data import get_region, pixel_size_meters

from backend.route_optimizer import calculate_route, NoRouteError

from backend.eva_planner import parse_settings, assess_eva

from backend.science_stops import get_science_stops

from backend.terrain_service import (
    get_terrain_summary,
    inspect_terrain,
    create_hazard_png
)

from backend.survival_simulator import (
    simulate_survival,
    get_defaults as get_survival_defaults
)

from backend.science_service import get_science_overview

app = Flask(
    __name__,
    static_folder="frontend",
    static_url_path=""
)


@app.route("/")
def home():
    return send_from_directory("frontend", "index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "application": "MARSWARD",
        "message": "Martian mission control is operational."
    })


@app.route("/api/config")
def config():
    """
    Region and dataset details the frontend needs to draw the
    map, so nothing about the dataset is hard-coded in the page.
    """

    try:
        region = get_region()
        rows, columns = region["elevation"].shape

        return jsonify({
            "status": "success",
            "region": {
                "name": region["name"],
                "bounds": region["bounds"],
                "raster_rows": int(rows),
                "raster_columns": int(columns),
                "pixels_per_degree": region["pixels_per_degree"],
                "pixel_size_m": round(pixel_size_meters(region), 1)
            },
            "dataset": {
                "name": region["dataset"]["name"],
                "short_name": region["dataset"]["short_name"]
            }
        })

    except Exception:
        app.logger.exception("Config failed")

        return jsonify({
            "error": "Terrain data is unavailable."
        }), 500


@app.route("/api/route", methods=["POST"])
def generate_route():

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "error": "Missing route information."
            }), 400

        start = data.get("start")
        destination = data.get("destination")

        if (
            not isinstance(start, list)
            or not isinstance(destination, list)
            or len(start) != 2
            or len(destination) != 2
        ):
            return jsonify({
                "error": "Provide start and destination as [longitude, latitude]."
            }), 400

        try:
            start = [float(value) for value in start]
            destination = [float(value) for value in destination]
        except (ValueError, TypeError):
            return jsonify({
                "error": "Coordinates must be numeric."
            }), 400

        # EVA settings are optional; defaults apply when absent.
        settings = parse_settings(data.get("eva"))

        try:
            result = calculate_route(
                start,
                destination,
                max_slope_degrees=settings["max_slope_degrees"]
            )

        except NoRouteError as error:

            # Not a failure: the answer is NO-GO, with the reason.
            return jsonify({
                "status": "no_route",
                "message": str(error),
                "route": None,
                "verdict": assess_eva(
                    None,
                    settings,
                    no_route_reason=str(error)
                )
            })

        return jsonify({
            "status": "success",
            "route": result,
            "verdict": assess_eva(result, settings)
        })

    except ValueError as error:

        return jsonify({
            "error": str(error)
        }), 400

    except Exception as error:

        app.logger.exception("Route calculation failed")

        return jsonify({
            "error": "An internal route calculation error occurred."
        }), 500


@app.route("/api/terrain/summary")
def terrain_summary():
    try:
        return jsonify(get_terrain_summary())

    except Exception:
        app.logger.exception("Terrain summary failed")

        return jsonify({
            "error": "Unable to retrieve terrain summary."
        }), 500


@app.route("/api/terrain/inspect")
def terrain_inspect():
    try:
        longitude = request.args.get("lon", type=float)
        latitude = request.args.get("lat", type=float)

        if longitude is None or latitude is None:
            return jsonify({
                "error": "Provide longitude and latitude."
            }), 400

        result = inspect_terrain(longitude, latitude)

        return jsonify(result)

    except ValueError as error:
        return jsonify({
            "error": str(error)
        }), 400

    except Exception:
        app.logger.exception("Terrain inspection failed")

        return jsonify({
            "error": "Unable to inspect selected terrain."
        }), 500


@app.route("/api/terrain/hazard-overlay")
def terrain_hazard_overlay():
    try:
        png_data = create_hazard_png()

        return send_file(
            BytesIO(png_data),
            mimetype="image/png",
            download_name="jezero_hazard_overlay.png"
        )

    except Exception:
        app.logger.exception("Hazard overlay generation failed")

        return jsonify({
            "error": "Unable to generate hazard overlay."
        }), 500


# --------------------------------------------------
# SURVIVAL SIMULATOR
# --------------------------------------------------

@app.route("/api/survival/defaults")
def survival_defaults():
    return jsonify(get_survival_defaults())


@app.route("/api/survival/simulate", methods=["POST"])
def survival_simulate():
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "error": "Missing survival simulation inputs."
            }), 400

        return jsonify(simulate_survival(data))

    except ValueError as error:
        return jsonify({
            "error": str(error)
        }), 400

    except Exception:
        app.logger.exception("Survival simulation failed")

        return jsonify({
            "error": "An internal survival simulation error occurred."
        }), 500


# --------------------------------------------------
# SCIENCE EXPLORER
# --------------------------------------------------

@app.route("/api/science/stops")
def science_stops():
    try:
        return jsonify({
            "status": "success",
            "stops": get_science_stops()
        })

    except Exception:
        app.logger.exception("Science stops failed")

        return jsonify({
            "error": "Unable to retrieve science stops."
        }), 500


@app.route("/api/science/overview")
def science_overview():
    try:
        return jsonify(get_science_overview())

    except Exception:
        app.logger.exception("Science overview failed")

        return jsonify({
            "error": "Unable to retrieve science overview."
        }), 500


if __name__ == "__main__":
    app.run(debug=True)