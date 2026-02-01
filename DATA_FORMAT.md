# Robot Data Format

## Updated Data Structure

The database now accepts and stores robot run data with the following format:

### Input Format (POST to `/ingest`)

```json
{
  "robot_id": "robot_001",
  "run_number": 1,
  "logs": [
    {
      "section_id": 1,           // 1 = Red Path, 2 = Ramp, 3 = Green Path
      "timestamp": 1500,         // Milliseconds since robot started
      "checkpoint_success": 1,   // 1 = Hit Blue Circle, 0 = Missed
      "ultrasonic_distance": 28, // Distance in cm during obstacle navigation
      "claw_status": 45          // Servo angle 0-180° (0 = closed, 180 = open)
    }
  ],
  "metadata": {
    "duration_ms": 12000,
    "competition": "Competition Name",
    "notes": "Any additional notes"
  }
}
```

### Section IDs

| ID | Section Name |
|----|-------------|
| 1  | Red Path    |
| 2  | Ramp        |
| 3  | Green Path  |

### Field Descriptions

- **section_id**: Which section of the course the robot is in (1, 2, or 3)
- **timestamp**: Total time in milliseconds since the robot started
- **checkpoint_success**: Whether the robot hit the blue checkpoint circle (1 = success, 0 = miss)
- **ultrasonic_distance**: Raw distance in centimeters recorded by the ultrasonic sensor
- **claw_status**: Current servo angle of the claw (0-180°, where 0 is typically closed)

## Analysis Metrics

When you click "Analyze Run", the system will calculate:

- **Section Times**: How long the robot spent in each section
- **Checkpoint Success Rate**: Percentage of checkpoints successfully hit
- **Ultrasonic Stats**: Average and minimum distances (for obstacle navigation analysis)
- **Claw Changes**: Number of significant claw position changes
- **Phase-Based Event Timeline**: Automatic detection of mission milestones (see below)
- **Detected Issues**: Automatic detection of problems like:
  - Slow sections (>15 seconds)
  - Low checkpoint success rate (<50%)
  - Very close obstacle encounters (<10cm)

### Phase-Based Event Detection

The system automatically detects and timestamps key mission events:

**Phase 1: Starting & Unlocking**
- Robot leaves BEGIN area (first timestamp)
- Claw closes to pick up box (servo angle: >90° → <45°)
- Reaches blue circle checkpoint (first checkpoint_success=1)
- Claw opens to drop box in white zone (servo angle: <45° → >90°)

**Phase 2: Target Shooting (Green Path - Ramp)**
- Begins ramp climb (section_id changes to 2)
- Reaches Purple Re-upload Point at top (midpoint of ramp section)
- Finishes ramp descent (end of section_id=2)

**Phase 3: Obstacle Course (Red Path)**
- Enters winding red path (section_id=1)
- Detects first black obstruction (ultrasonic_distance < 15cm)
- Successfully clears final obstacle (ultrasonic_distance returns to >30cm)
- Exits red path (end of section_id=1)

**Phase 4: Mission Conclusion**
- (Optional) Second box picked up (second claw close event)
- Crosses BEGIN line to finish (last timestamp)

## Frontend Display

The Data page now shows:

1. **Runs List**: All robot runs with metadata
2. **Analysis Section**:
   - AI-generated summary and recommendations
   - **Mission Timeline**: Phase-based event timeline showing key milestones with timestamps
   - Section path visualization
   - Section times breakdown
   - Performance metrics (checkpoint rate, ultrasonic avg, claw changes)
   - Detected issues
3. **Raw Sensor Readings Table** (expandable):
   - Time
   - Section (Red Path, Ramp, Green Path)
   - Checkpoint (✓ Hit or ✗ Miss)
   - Ultrasonic distance
   - Claw angle

## Test Data

Run `python3 backend/test_data.py` to add 3 sample runs with realistic data:

Each run contains **3000 sensor readings** captured every **100ms** for **5 minutes** (300 seconds):

- **Robot 001, Run #1**: Excellent performance
  - 95% checkpoint success rate
  - Smooth section transitions (1min → 3min → 5min)
  - Stable ultrasonic readings (~35cm average)

- **Robot 001, Run #2**: Poor performance
  - 50% checkpoint success rate
  - Slow section transitions (2min → 4.2min → 5min)
  - Close obstacle encounters (~20cm average)

- **Robot 002, Run #1**: Good performance
  - 75% checkpoint success rate
  - Normal section transitions (1.5min → 3.3min → 5min)
  - Moderate ultrasonic readings (~28cm average)

### Data Generation Features:
- Realistic sensor fluctuations
- Section-based progression (Red Path → Ramp → Green Path)
- Smooth claw movements with periodic target changes
- Random obstacle encounters (5% probability)
- Performance-based checkpoint success rates
