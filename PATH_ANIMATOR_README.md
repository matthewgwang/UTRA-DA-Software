# Robot Path Animator

A React + Flask feature that animates a robot drawing a predetermined path in real-time.

## Overview

The path animator visually demonstrates a robot traversing and drawing a known path. The animation speed is controlled by changing segment durations without modifying the path geometry.

## Features

- **SVG-based rendering** with smooth animations
- **Sequential segment drawing** using stroke-dasharray/stroke-dashoffset
- **Robot icon movement** along the path using getPointAtLength()
- **Automatic viewBox calculation** to fit the entire path
- **Playback controls**: Start, Pause/Resume, Reset
- **Real-time progress tracking** showing current segment

## Usage

### 1. Start the Backend

```bash
cd backend
python3 app.py
```

The Flask server will run on `http://localhost:5001`

### 2. Start the Frontend

```bash
cd frontend
npm run dev
```

The React app will run on `http://localhost:5173`

### 3. Navigate to Path Animator

Open your browser and go to:
```
http://localhost:5173/animator
```

Or click "Path Animator" in the navigation menu.

## Data Format

Path data is defined as an array of segments. Each segment is a straight line from start → end with a duration.

```javascript
const segments = [
  {
    "id": "s1",                    // Unique segment identifier
    "points": [[0, 0], [0, 44]],   // [start, end] coordinates
    "durationSec": 10              // Time to draw this segment (seconds)
  },
  {
    "id": "s2",
    "points": [[0, 44], [0, 87.6]],
    "durationSec": 5
  }
  // ... more segments
];
```

### Coordinate System

- 2D coordinates: `[x, y]`
- Units are arbitrary (e.g., cm, pixels, meters)
- Origin at `[0, 0]`
- Coordinates can be positive or negative

## Customization

### Changing the Path Data

**Backend (Recommended):**

Edit `/backend/app.py` at the `/api/path` route (around line 475):

```python
@app.route("/api/path", methods=["GET"])
def get_path_data():
    # Replace this segments array with your own data
    segments = [
        {"id": "s1", "points": [[0, 0], [10, 20]], "durationSec": 2},
        {"id": "s2", "points": [[10, 20], [30, 40]], "durationSec": 3},
        # Add more segments...
    ]

    return jsonify({
        "segments": segments,
        "total_duration": sum(seg["durationSec"] for seg in segments),
        "total_segments": len(segments)
    })
```

**Options for loading path data:**
1. **Hardcoded**: Define segments directly in the route (as shown above)
2. **From Database**: Query MongoDB for stored path configurations
3. **From File**: Load from JSON/CSV file
4. **From Robot Run**: Extract actual path from telemetry data

Example - Load from file:
```python
import json

@app.route("/api/path", methods=["GET"])
def get_path_data():
    with open('paths/default_path.json', 'r') as f:
        data = json.load(f)
    return jsonify(data)
```

Example - From database:
```python
@app.route("/api/path", methods=["GET"])
def get_path_data():
    path_id = request.args.get("path_id", "default")
    path_doc = paths_collection.find_one({"path_id": path_id})

    if not path_doc:
        return jsonify({"error": "Path not found"}), 404

    return jsonify({
        "segments": path_doc["segments"],
        "total_duration": path_doc["total_duration"],
        "total_segments": len(path_doc["segments"])
    })
```

### Changing Animation Appearance

Edit `/frontend/src/PathAnimator.jsx`:

**Robot Icon:**
```jsx
// Change size
<circle r="8" ... />  // Default is r="5"

// Change color
<circle fill="#ff0000" ... />  // Default is "#e53e3e"

// Replace with image
<image
  href="/robot-icon.svg"
  x={point.x - 10}
  y={point.y - 10}
  width="20"
  height="20"
/>
```

**Path Line:**
```jsx
<line
  stroke="#0000ff"      // Change color (default: "#6fbf8f")
  strokeWidth="5"       // Change thickness (default: 3)
  strokeLinecap="round" // round, square, butt
/>
```

**Guide Lines (dotted):**
```jsx
<line
  stroke="#cccccc"      // Change guide line color
  strokeDasharray="2 4" // Change dash pattern
/>
```

### Changing Timing

**Initial delay before animation:**
```jsx
// In startAnimation() function
setTimeout(() => {
  segmentStartTimeRef.current = performance.now();
  animateSegment(0, segmentStartTimeRef.current);
}, 400);  // Change from 400ms to desired delay
```

**Segment durations:**
Update the `durationSec` values in your path data (backend).

## Component API

The PathAnimator component provides these internal functions:

### `startAnimation()`
Begins the animation sequence after a short delay.

### `resetAnimation()`
Resets all segments to initial state and hides the robot.

### `pauseAnimation()`
Pauses the current animation.

### `resumeAnimation()`
Resumes from the paused position.

## Technical Details

### SVG Animation Technique

Each segment uses:
- **stroke-dasharray**: Set to line length
- **stroke-dashoffset**: Animated from line length → 0 to create drawing effect
- **getPointAtLength()**: Calculates robot position along the path

### ViewBox Calculation

Automatically computes the bounding box of all path points and adds 20% padding:

```javascript
const calculateViewBox = (segments) => {
  // Find min/max x and y coordinates
  // Add padding
  // Return "minX minY width height"
}
```

## File Structure

```
frontend/
  src/
    PathAnimator.jsx       # Main component
    animator.css           # Styling
    App.jsx               # Routing (includes /animator route)

backend/
  app.py                  # Flask routes (includes /api/path endpoint)
```

## Extending the Feature

### Add Multiple Paths

**Backend:**
```python
@app.route("/api/path/<path_name>", methods=["GET"])
def get_named_path(path_name):
    paths = {
        "square": [...],
        "circle": [...],
        "zigzag": [...]
    }

    if path_name not in paths:
        return jsonify({"error": "Path not found"}), 404

    return jsonify({"segments": paths[path_name]})
```

**Frontend:**
```jsx
const fetchPathData = async (pathName = "default") => {
  const response = await fetch(`${API_URL}/api/path/${pathName}`);
  // ...
}
```

### Add Playback Speed Control

```jsx
const [playbackSpeed, setPlaybackSpeed] = useState(1.0);

// In animate function:
const adjustedDuration = segment.durationSec / playbackSpeed;
const progress = Math.min(elapsed / adjustedDuration, 1);
```

### Export Animation as Video/GIF

Use a library like `html2canvas` or `canvas-recorder` to record the SVG animation.

## Troubleshooting

**Path not displaying:**
- Check browser console for errors
- Verify backend is running on port 5001
- Ensure CORS is enabled (already configured in Flask)

**Animation too fast/slow:**
- Adjust `durationSec` values in segment data
- Check that timing is in seconds, not milliseconds

**Robot not moving:**
- Verify robot circle has `ref={robotRef}`
- Check that path segments have correct `id` attributes
- Ensure `getPointAtLength()` is supported (modern browsers only)

**ViewBox not fitting path:**
- Manually set viewBox if automatic calculation fails
- Check that all coordinates are valid numbers

## Example: Converting Robot Telemetry to Path

To convert actual robot run data into path segments:

```python
@app.route("/api/path/from-run/<run_id>", methods=["GET"])
def get_path_from_run(run_id):
    run = runs_collection.find_one({"_id": ObjectId(run_id)})
    if not run:
        return jsonify({"error": "Run not found"}), 404

    logs = run.get("logs", [])
    segments = []

    # Sample every Nth log to create segments
    sample_rate = 100  # Use every 100th log
    for i in range(0, len(logs) - sample_rate, sample_rate):
        start_log = logs[i]
        end_log = logs[i + sample_rate]

        # Assuming logs have x, y coordinates
        segments.append({
            "id": f"seg_{i}",
            "points": [
                [start_log.get("x", 0), start_log.get("y", 0)],
                [end_log.get("x", 0), end_log.get("y", 0)]
            ],
            "durationSec": (end_log["timestamp_ms"] - start_log["timestamp_ms"]) / 1000
        })

    return jsonify({"segments": segments})
```

## Next Steps

- Add curved path support (Bezier curves, arcs)
- Multiple robots on the same canvas
- Collision detection visualization
- Path editing interface
- 3D visualization (using Three.js)
- Real-time path generation from live telemetry
