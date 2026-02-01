import os
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import requests

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))
DIST_DIR = os.path.join(FRONTEND_DIR, "dist")  # Vite production build output

# Create Flask app (API + optional static serving)
app = Flask(__name__)
CORS(app)

# -----------------------------------------------------------------------------
# MongoDB Configuration
# -----------------------------------------------------------------------------
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/utra_da")
client = MongoClient(MONGODB_URI)

# If URI explicitly includes a DB, get_default_database() can work.
# Otherwise, fall back to a known DB name.
try:
    db = client.get_default_database()
except Exception:
    db = client["utra_da"]

runs_collection = db["runs"]
telemetry_collection = db["telemetry"]

# -----------------------------------------------------------------------------
# OpenRouter Configuration
# -----------------------------------------------------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Event code mappings (from Arduino EEPROM)
EVENT_CODES = {
    1: "Start",
    2: "ZoneChange",
    3: "Shot",
    4: "Obstacle",
    5: "Stop",
    6: "Error"
}

ZONE_NAMES = {
    0: "Start",
    1: "Red Zone",
    2: "Blue Zone",
    3: "Green Zone",
    4: "Center",
    5: "Unknown"
}

# Section names for new sensor data format
SECTION_NAMES = {
    1: "Red Path",
    2: "Ramp",
    3: "Green Path"
}


def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable dict."""
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    if "created_at" in doc and doc["created_at"]:
        doc["created_at"] = doc["created_at"].isoformat()
    if "analyzed_at" in doc and doc["analyzed_at"]:
        doc["analyzed_at"] = doc["analyzed_at"].isoformat()
    return doc


# -----------------------------------------------------------------------------
# API Routes
# -----------------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})


@app.route("/ingest", methods=["POST"])
def ingest_data():
    """
    POST /ingest
    Save raw JSON logs from robot EEPROM to MongoDB.
    Supports multiple formats:
    - Path format: includes x,y positions, segments, and events
    - Sensor format: section_id based
    - Event format: Arduino EEPROM events
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        if "logs" not in data:
            return jsonify({"error": "Missing 'logs' field"}), 400

        processed_logs = []
        raw_logs = data.get("logs", [])

        # Detect format based on first log entry
        has_position = raw_logs and "x" in raw_logs[0] and "y" in raw_logs[0]
        is_sensor_format = raw_logs and "section_id" in raw_logs[0]

        # Determine data format
        if has_position:
            data_format = "path"
        elif is_sensor_format:
            data_format = "sensor"
        else:
            data_format = "event"

        for log in raw_logs:
            if has_position:
                # New path format with x,y positions
                section_id = log.get("section_id", 0)
                processed_logs.append({
                    "x": log.get("x", 0),
                    "y": log.get("y", 0),
                    "segment_id": log.get("segment_id", ""),
                    "segment_index": log.get("segment_index", 0),
                    "section_id": section_id,
                    "section_name": SECTION_NAMES.get(section_id, "Unknown"),
                    "timestamp_ms": log.get("timestamp", 0),
                    "checkpoint_success": log.get("checkpoint_success", 0),
                    "ultrasonic_distance": log.get("ultrasonic_distance", 0),
                    "claw_status": log.get("claw_status", 0),
                })
            elif is_sensor_format:
                # Sensor data format
                section_id = log.get("section_id", 0)
                processed_logs.append({
                    "section_id": section_id,
                    "section_name": SECTION_NAMES.get(section_id, "Unknown"),
                    "timestamp_ms": log.get("timestamp", 0),
                    "checkpoint_success": log.get("checkpoint_success", 0),
                    "ultrasonic_distance": log.get("ultrasonic_distance", 0),
                    "claw_status": log.get("claw_status", 0),
                    "raw": log
                })
            else:
                # Old event-based format from Arduino EEPROM
                event_code = log.get("event", 0)
                zone_id = log.get("data", 0)
                processed_logs.append({
                    "event_code": event_code,
                    "event_name": EVENT_CODES.get(event_code, "Unknown"),
                    "zone_id": zone_id,
                    "zone_name": ZONE_NAMES.get(zone_id, "Unknown"),
                    "timestamp_ms": log.get("timestamp", 0),
                    "raw": log
                })

        run_doc = {
            "robot_id": data.get("robot_id", "unknown"),
            "run_number": data.get("run_number", 0),
            "logs": processed_logs,
            "events": data.get("events", []),  # Store events separately
            "segments": data.get("segments", []),  # Store segment data
            "metadata": data.get("metadata", {}),
            "data_format": data_format,
            "created_at": datetime.utcnow(),
            "analyzed": False,
            "analysis": None
        }

        result = runs_collection.insert_one(run_doc)

        return jsonify({
            "success": True,
            "run_id": str(result.inserted_id),
            "logs_count": len(processed_logs),
            "events_count": len(data.get("events", [])),
            "segments_count": len(data.get("segments", []))
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/runs", methods=["GET"])
def get_runs():
    """GET /runs - list runs (supports pagination and robot_id filter)."""
    try:
        robot_id = request.args.get("robot_id")
        limit = int(request.args.get("limit", 50))
        skip = int(request.args.get("skip", 0))

        query = {}
        if robot_id:
            query["robot_id"] = robot_id

        runs = list(
            runs_collection.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        serialized_runs = []
        for run in runs:
            serialized_runs.append({
                "_id": str(run["_id"]),
                "robot_id": run.get("robot_id"),
                "run_number": run.get("run_number"),
                "logs_count": len(run.get("logs", [])),
                "created_at": run.get("created_at").isoformat() if run.get("created_at") else None,
                "analyzed": run.get("analyzed", False),
                "metadata": run.get("metadata", {})
            })

        total_count = runs_collection.count_documents(query)

        return jsonify({
            "runs": serialized_runs,
            "total": total_count,
            "limit": limit,
            "skip": skip
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/runs/<run_id>", methods=["GET"])
def get_run_detail(run_id):
    try:
        run = runs_collection.find_one({"_id": ObjectId(run_id)})
        if not run:
            return jsonify({"error": "Run not found"}), 404
        return jsonify(serialize_doc(run))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/runs/clear", methods=["DELETE"])
def clear_all_runs():
    """DELETE /runs/clear - delete all runs from the database."""
    try:
        result = runs_collection.delete_many({})
        return jsonify({
            "success": True,
            "deleted_count": result.deleted_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/analyze", methods=["POST"])
def analyze_run():
    """
    POST /analyze
    Send run data to OpenRouter and return AI critique.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        if "run_id" in data:
            run = runs_collection.find_one({"_id": ObjectId(data["run_id"])})
            if not run:
                return jsonify({"error": "Run not found"}), 404
            logs = run.get("logs", [])
            metadata = run.get("metadata", {})
            run_id = data["run_id"]
        else:
            logs = data.get("logs", [])
            metadata = data.get("metadata", {})
            run_id = None

        if not logs:
            return jsonify({"error": "No logs to analyze"}), 400

        # Detect data format
        is_sensor_format = "section_id" in logs[0] if logs else False

        timeline = []
        issues = []
        section_times = {}
        section_sequence = []

        if is_sensor_format:
            # Analyze sensor format data
            prev_section = None
            prev_claw = None
            checkpoint_hits = 0
            checkpoint_misses = 0
            ultrasonic_readings = []

            for i, log in enumerate(logs):
                timestamp_ms = log.get("timestamp_ms", 0)
                section_id = log.get("section_id", 0)
                section_name = log.get("section_name", "Unknown")
                checkpoint = log.get("checkpoint_success", 0)
                ultrasonic = log.get("ultrasonic_distance", 0)
                claw = log.get("claw_status", 0)

                ultrasonic_readings.append(ultrasonic)

                # Track checkpoint hits/misses
                if checkpoint == 1:
                    checkpoint_hits += 1
                else:
                    checkpoint_misses += 1

                # Detect section changes
                if section_id != prev_section:
                    if prev_section is not None:
                        timeline.append({
                            "time_ms": timestamp_ms,
                            "event": f"Entered {section_name}"
                        })
                    section_sequence.append(section_name)
                    prev_section = section_id

                # Detect claw movements (picking up / dropping)
                if prev_claw is not None:
                    if prev_claw < 90 and claw >= 90:
                        timeline.append({
                            "time_ms": timestamp_ms,
                            "event": "Claw closed (picking up)"
                        })
                    elif prev_claw >= 90 and claw < 90:
                        timeline.append({
                            "time_ms": timestamp_ms,
                            "event": "Claw opened (dropping)"
                        })
                prev_claw = claw

                # Detect obstacles (ultrasonic < 15cm)
                if ultrasonic < 15 and (i == 0 or logs[i-1].get("ultrasonic_distance", 50) >= 15):
                    timeline.append({
                        "time_ms": timestamp_ms,
                        "event": f"Obstacle detected ({ultrasonic}cm)"
                    })

            # Add start and end milestones
            if logs:
                timeline.insert(0, {"time_ms": 0, "event": "Run started"})
                timeline.append({"time_ms": logs[-1].get("timestamp_ms", 0), "event": "Run completed"})

            # Sort timeline by time
            timeline.sort(key=lambda x: x["time_ms"])

            # Calculate section times
            current_section = None
            section_start = 0
            for log in logs:
                section_name = log.get("section_name", "Unknown")
                timestamp_ms = log.get("timestamp_ms", 0)
                if section_name != current_section:
                    if current_section is not None:
                        section_times[current_section] = section_times.get(current_section, 0) + (timestamp_ms - section_start)
                    current_section = section_name
                    section_start = timestamp_ms
            # Add final section time
            if current_section and logs:
                section_times[current_section] = section_times.get(current_section, 0) + (logs[-1].get("timestamp_ms", 0) - section_start)

            # Calculate metrics
            total_checkpoints = checkpoint_hits + checkpoint_misses
            checkpoint_rate = (checkpoint_hits / total_checkpoints * 100) if total_checkpoints > 0 else 0
            ultrasonic_avg = sum(ultrasonic_readings) / len(ultrasonic_readings) if ultrasonic_readings else 0

            # Detect issues
            for section, time_ms in section_times.items():
                if time_ms > 120000:  # More than 2 minutes in one section
                    issues.append(f"Long time in {section}: {time_ms/1000:.1f}s")

            if checkpoint_rate < 60:
                issues.append(f"Low checkpoint success rate: {checkpoint_rate:.1f}%")

        else:
            # Original event-based format analysis
            zone_sequence = [log["zone_name"] for log in logs if log.get("event_name") == "ZoneChange"]
            event_summary = {}
            for log in logs:
                event_name = log.get("event_name", "Unknown")
                event_summary[event_name] = event_summary.get(event_name, 0) + 1

            for i, log in enumerate(logs):
                if log.get("event_name") == "ZoneChange":
                    zone = log["zone_name"]
                    start_time = log["timestamp_ms"]
                    end_time = logs[i + 1]["timestamp_ms"] if i + 1 < len(logs) else start_time
                    section_times[zone] = section_times.get(zone, 0) + (end_time - start_time)

            for zone, time_ms in section_times.items():
                if time_ms > 10000:
                    issues.append(f"Stuck in {zone}: {time_ms/1000:.1f}s")

            oscillations = 0
            for i in range(2, len(zone_sequence)):
                if zone_sequence[i] == zone_sequence[i - 2] and zone_sequence[i] != zone_sequence[i - 1]:
                    oscillations += 1
            if oscillations > 2:
                issues.append(f"Oscillation detected: {oscillations} times")

            section_sequence = zone_sequence
            checkpoint_rate = None
            ultrasonic_avg = None

        prompt = f"""You are an expert robotics coach analyzing a competition run.
Analyze this robot's performance and provide actionable feedback.

Run Summary:
- Total Events: {len(logs)}
- Section Sequence: {' -> '.join(section_sequence) if section_sequence else 'No section changes recorded'}
- Time in Sections (ms): {section_times}
- Detected Issues: {issues if issues else 'None detected'}

Full Event Log (first 50):
{logs[:50]}

Please provide:
1. A brief performance summary
2. Identified issues (e.g., oscillation, stuck behavior, inefficient pathing)
3. Specific recommendations with actionable fixes
4. An overall score out of 10
"""

        # Build base analysis with timeline and metrics
        base_analysis = {
            "timeline": timeline,
            "section_sequence": section_sequence,
            "section_times": section_times,
            "issues": issues,
        }

        # Add sensor-specific metrics if available
        if is_sensor_format:
            base_analysis["checkpoint_rate"] = checkpoint_rate
            base_analysis["ultrasonic_avg"] = ultrasonic_avg

        if not OPENROUTER_API_KEY:
            analysis = {
                **base_analysis,
                "summary": "OPENROUTER_API_KEY not configured. This is a mock analysis.",
                "recommendations": ["Configure OPENROUTER_API_KEY in .env for real AI analysis."],
                "score": 0,
            }
        else:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://utra-da.local",
                "X-Title": "UTRA Data Analysis"
            }
            payload = {
                "model": "google/gemini-3-flash-preview",
                "messages": [
                    {"role": "system", "content": "You are an expert robotics competition coach."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1000
            }

            response = requests.post(OPENROUTER_URL, json=payload, headers=headers)
            response.raise_for_status()

            ai_response = response.json()
            raw_content = ai_response["choices"][0]["message"]["content"]

            analysis = {
                **base_analysis,
                "summary": raw_content,
                "raw_response": raw_content,
                "model_used": ai_response.get("model", "unknown"),
                "usage": ai_response.get("usage", {}),
            }

        if run_id:
            runs_collection.update_one(
                {"_id": ObjectId(run_id)},
                {"$set": {"analyzed": True, "analysis": analysis, "analyzed_at": datetime.utcnow()}}
            )

        return jsonify({"success": True, "analysis": analysis})

    except requests.RequestException as e:
        return jsonify({"error": f"OpenRouter API error: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/telemetry", methods=["POST"])
def ingest_telemetry():
    """POST /telemetry - ingest live telemetry."""
    try:
        data = request.get_json() or {}
        telemetry_doc = {
            "robot_id": data.get("robot_id", "unknown"),
            "sensors": data.get("sensors", {}),
            "timestamp": datetime.utcnow()
        }
        telemetry_collection.insert_one(telemetry_doc)
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/telemetry/latest", methods=["GET"])
def get_latest_telemetry():
    """GET /telemetry/latest - latest telemetry reading."""
    try:
        robot_id = request.args.get("robot_id")
        query = {"robot_id": robot_id} if robot_id else {}

        telemetry = telemetry_collection.find_one(query, sort=[("timestamp", -1)])
        if telemetry:
            telemetry["_id"] = str(telemetry["_id"])
            telemetry["timestamp"] = telemetry["timestamp"].isoformat()
            return jsonify(telemetry)
        return jsonify({"message": "No telemetry data found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_default_segments():
    """Returns the default path segments for animation."""
    return [
        {"id": "s1", "points": [[0, 0], [0, -600]], "duration": 3000},
        {"id": "s2", "points": [[0, -600], [150, -1125]], "duration": 4000, "pause_duration": 2000, "pause_message": "📦 Picking Up Box"},
        {"id": "s3", "points": [[150, -1125], [300, -1350]], "duration": 3000},
        {"id": "s4", "points": [[300, -1350], [600, -1575]], "duration": 4000},
        {"id": "s5", "points": [[600, -1575], [525, -1800]], "duration": 3000, "pause_duration": 2000, "pause_message": "⚽ Shooting"},
        {"id": "s6", "points": [[525, -1800], [375, -1650]], "duration": 3000},
        {"id": "s7", "points": [[375, -1650], [150, -1125]], "duration": 3000, "pause_duration": 2000, "pause_message": "📦 Dropping Box"},
        {"id": "s8", "points": [[150, -1125], [0, -600]], "duration": 3000},
        {"id": "s9", "points": [[0, -600], [-120, -825]], "duration": 3000, "pause_duration": 2000, "pause_message": "📦 Picking Up Box"},
        {"id": "s10", "points": [[-120, -825], [-195, -975]], "duration": 3000},
        {"id": "s11", "points": [[-195, -975], [-300, -1125]], "duration": 3000},
        {"id": "s12", "points": [[-300, -1125], [-525, -975]], "duration": 3000},
        {"id": "s13", "points": [[-525, -975], [-675, -1200]], "duration": 3000},
        {"id": "s14", "points": [[-675, -1200], [-600, -1650]], "duration": 3000, "pause_duration": 2000, "pause_message": "🚧 Avoiding Obstacle"},
        {"id": "s15", "points": [[-600, -1650], [-630, -1695]], "duration": 3000},
        {"id": "s16", "points": [[-630, -1695], [-900, -2100]], "duration": 3000},
        {"id": "s17", "points": [[-900, -2100], [-975, -1950]], "duration": 3000},
        {"id": "s18", "points": [[-975, -1950], [-1050, -1725]], "duration": 3000},
        {"id": "s19", "points": [[-1050, -1725], [-975, -1575]], "duration": 3000, "pause_duration": 2000, "pause_message": "🚧 Avoiding Obstacle"},
        {"id": "s20", "points": [[-975, -1575], [-900, -1125]], "duration": 3000, "pause_duration": 2000, "pause_message": "📦 Drop Box"},
        {"id": "s21", "points": [[-900, -1125], [-825, -825]], "duration": 3000},
        {"id": "s22", "points": [[-825, -825], [0, -600]], "duration": 3000}
    ]


@app.route("/api/path", methods=["GET"])
def get_path():
    """GET /api/path - returns default path segments for animation."""
    try:
        segments = get_default_segments()
        return jsonify({"segments": segments})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


ACTION_EMOJIS = {
    "pickup_box": "📦",
    "drop_box": "📦",
    "shooting": "⚽",
    "avoid_obstacle": "🚧",
    "stuck": "⚠️",
    "start": "🚀",
    "end": "🏁"
}

ACTION_MESSAGES = {
    "pickup_box": "Picking Up Box",
    "drop_box": "Dropping Box",
    "shooting": "Shooting Ball",
    "avoid_obstacle": "Avoiding Obstacle",
    "stuck": "Robot Stuck",
    "start": "Run Started",
    "end": "Run Completed"
}


def generate_segments_from_run(run):
    """Generate path segments from actual run data."""
    segments = []
    stored_segments = run.get("segments", [])
    events = run.get("events", [])

    # Create event lookup by segment_id
    event_by_segment = {}
    for event in events:
        seg_id = event.get("segment_id")
        if seg_id and event.get("event_type") not in ["start", "end"]:
            event_by_segment[seg_id] = event

    if stored_segments:
        # Use stored segment data with actual timings
        for seg in stored_segments:
            segment_id = seg.get("segment_id", f"s{seg.get('segment_index', 0) + 1}")
            start_pos = seg.get("start_pos", [0, 0])
            end_pos = seg.get("end_pos", [0, 0])
            duration = seg.get("duration", 1000)
            action = seg.get("action")

            segment_data = {
                "id": segment_id,
                "points": [start_pos, end_pos],
                "duration": duration
            }

            # Add pause info from events
            if segment_id in event_by_segment:
                event = event_by_segment[segment_id]
                pause_duration = event.get("pause_duration", 0)
                if pause_duration > 0:
                    event_type = event.get("event_type", "")
                    emoji = ACTION_EMOJIS.get(event_type, "")
                    message = ACTION_MESSAGES.get(event_type, event.get("message", ""))
                    segment_data["pause_duration"] = pause_duration
                    segment_data["pause_message"] = f"{emoji} {message}".strip()
            elif action:
                # Fallback to action field if no event found
                emoji = ACTION_EMOJIS.get(action, "")
                message = ACTION_MESSAGES.get(action, action)
                segment_data["pause_duration"] = 1500
                segment_data["pause_message"] = f"{emoji} {message}".strip()

            segments.append(segment_data)

    return segments


@app.route("/api/path/<run_id>", methods=["GET"])
def get_path_for_run(run_id):
    """GET /api/path/<run_id> - returns path segments for a specific run."""
    try:
        run = runs_collection.find_one({"_id": ObjectId(run_id)})
        if not run:
            return jsonify({"error": "Run not found"}), 404

        # Check if run has segment data
        if run.get("segments") or run.get("data_format") == "path":
            segments = generate_segments_from_run(run)
            if segments:
                # Also return events for timeline display
                events = run.get("events", [])
                return jsonify({
                    "segments": segments,
                    "events": events,
                    "metadata": run.get("metadata", {}),
                    "duration_ms": run.get("metadata", {}).get("duration_ms", 0)
                })

        # Fallback to default segments
        segments = get_default_segments()
        return jsonify({"segments": segments})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------------------------------------------------------
# Frontend Serving (Production Build)
# -----------------------------------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """
    Serve the built React frontend (frontend/dist).
    If dist does not exist, return a helpful message.
    """
    if os.path.isdir(DIST_DIR):
        if path != "" and os.path.exists(os.path.join(DIST_DIR, path)):
            return send_from_directory(DIST_DIR, path)
        return send_from_directory(DIST_DIR, "index.html")

    return jsonify({
        "message": "Frontend build not found. Run `npm run build` in frontend/ to create dist/.",
        "hint": "For development, use Vite dev server at http://localhost:5173."
    }), 404


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    debug = os.getenv("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
