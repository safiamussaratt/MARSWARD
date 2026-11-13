
from flask import Flask, send_from_directory, jsonify, request

from backend.route_optimizer import calculate_route

from flask import send_file
from io import BytesIO

from backend.terrain_service import (
    get_terrain_summary,
    inspect_terrain,
    create_hazard_png
)

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

        result = calculate_route(start, destination)

        return jsonify({
            "status": "success",
            "route": result
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

if __name__ == "__main__":
    app.run(debug=True)
