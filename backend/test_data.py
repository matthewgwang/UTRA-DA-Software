#!/usr/bin/env python3
"""
Script to add sample test data to MongoDB for testing the frontend.
Generates realistic robot path data with x,y positions, segment transitions,
and events (pickup, dropoff, obstacle avoidance).
"""
import requests
import random
import math

API_URL = "http://localhost:5001"

# Define the path segments (same as in app.py but with more detail)
PATH_SEGMENTS = [
    {"id": "s1", "start": [0, 0], "end": [0, -600], "action": None},
    {"id": "s2", "start": [0, -600], "end": [150, -1125], "action": "pickup_box"},
    {"id": "s3", "start": [150, -1125], "end": [300, -1350], "action": None},
    {"id": "s4", "start": [300, -1350], "end": [600, -1575], "action": None},
    {"id": "s5", "start": [600, -1575], "end": [525, -1800], "action": "shooting"},
    {"id": "s6", "start": [525, -1800], "end": [375, -1650], "action": "drop_box"},
    {"id": "s7", "start": [375, -1650], "end": [150, -1125], "action": None},
    {"id": "s8", "start": [150, -1125], "end": [0, -600], "action": None},
    {"id": "s9", "start": [0, -600], "end": [-120, -825], "action": "pickup_box"},
    {"id": "s10", "start": [-120, -825], "end": [-195, -975], "action": None},
    {"id": "s11", "start": [-195, -975], "end": [-300, -1125], "action": None},
    {"id": "s12", "start": [-300, -1125], "end": [-525, -975], "action": None},
    {"id": "s13", "start": [-525, -975], "end": [-675, -1200], "action": None},
    {"id": "s14", "start": [-675, -1200], "end": [-600, -1650], "action": "avoid_obstacle"},
    {"id": "s15", "start": [-600, -1650], "end": [-630, -1695], "action": None},
    {"id": "s16", "start": [-630, -1695], "end": [-900, -2100], "action": None},
    {"id": "s17", "start": [-900, -2100], "end": [-975, -1950], "action": None},
    {"id": "s18", "start": [-975, -1950], "end": [-1050, -1725], "action": None},
    {"id": "s19", "start": [-1050, -1725], "end": [-975, -1575], "action": "avoid_obstacle"},
    {"id": "s20", "start": [-975, -1575], "end": [-900, -1125], "action": "drop_box"},
    {"id": "s21", "start": [-900, -1125], "end": [-825, -825], "action": None},
    {"id": "s22", "start": [-825, -825], "end": [0, -600], "action": None}
]

ACTION_MESSAGES = {
    "pickup_box": "Picking Up Box",
    "drop_box": "Dropping Box",
    "shooting": "Shooting Ball",
    "avoid_obstacle": "Avoiding Obstacle"
}


def generate_realistic_run(robot_id, run_number, performance_profile):
    """
    Generate realistic path data with x,y positions, segment timings, and events.

    performance_profile: "excellent", "good", "poor"
    - excellent: fast traversal, short pauses
    - good: normal speed, normal pauses
    - poor: slow traversal, long pauses, occasional stuck behavior
    """
    logs = []
    events = []
    segment_data = []

    # Performance multipliers
    if performance_profile == "excellent":
        speed_multiplier = 0.7  # 30% faster
        pause_multiplier = 0.5  # 50% shorter pauses
        stuck_chance = 0.02
    elif performance_profile == "good":
        speed_multiplier = 1.0
        pause_multiplier = 1.0
        stuck_chance = 0.05
    else:  # poor
        speed_multiplier = 1.5  # 50% slower
        pause_multiplier = 2.0  # 2x longer pauses
        stuck_chance = 0.15

    current_time = 0
    current_claw = 0  # 0 = open, 180 = closed

    for seg_idx, segment in enumerate(PATH_SEGMENTS):
        seg_id = segment["id"]
        start_pos = segment["start"]
        end_pos = segment["end"]
        action = segment["action"]

        # Calculate segment distance
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        distance = math.sqrt(dx*dx + dy*dy)

        # Base duration: 5ms per unit distance, adjusted by performance
        base_duration = int(distance * 5 * speed_multiplier)

        # Add some randomness (±20%)
        duration = int(base_duration * random.uniform(0.8, 1.2))
        duration = max(500, duration)  # Minimum 500ms per segment

        segment_start_time = current_time

        # Generate position readings every 100ms during segment traversal
        num_readings = max(1, duration // 100)

        for i in range(num_readings):
            progress = i / max(1, num_readings - 1) if num_readings > 1 else 1.0

            # Calculate position along segment
            x = start_pos[0] + dx * progress
            y = start_pos[1] + dy * progress

            # Add some noise to position (simulating sensor error)
            x += random.uniform(-5, 5)
            y += random.uniform(-5, 5)

            # Determine section based on y position
            if y > -800:
                section_id = 1  # Red Path (upper area)
            elif y > -1400:
                section_id = 2  # Ramp (middle area)
            else:
                section_id = 3  # Green Path (lower area)

            # Simulate ultrasonic readings
            if action == "avoid_obstacle" and 0.3 < progress < 0.7:
                ultrasonic = random.randint(8, 15)  # Close obstacle
            else:
                ultrasonic = random.randint(25, 45)  # Normal distance

            # Simulate checkpoint hits (80% success rate, varies by profile)
            checkpoint_success = 1 if random.random() < (0.95 if performance_profile == "excellent" else 0.75 if performance_profile == "good" else 0.55) else 0

            logs.append({
                "timestamp": current_time,
                "x": round(x, 1),
                "y": round(y, 1),
                "segment_id": seg_id,
                "segment_index": seg_idx,
                "section_id": section_id,
                "checkpoint_success": checkpoint_success,
                "ultrasonic_distance": ultrasonic,
                "claw_status": current_claw
            })

            current_time += 100

        segment_end_time = current_time

        # Record segment traversal
        segment_data.append({
            "segment_id": seg_id,
            "segment_index": seg_idx,
            "start_pos": start_pos,
            "end_pos": end_pos,
            "start_time": segment_start_time,
            "end_time": segment_end_time,
            "duration": segment_end_time - segment_start_time,
            "action": action
        })

        # Handle action (pause) at end of segment
        if action:
            # Base pause durations
            pause_durations = {
                "pickup_box": 2000,
                "drop_box": 1500,
                "shooting": 3000,
                "avoid_obstacle": 1000
            }

            base_pause = pause_durations.get(action, 1000)
            pause_duration = int(base_pause * pause_multiplier * random.uniform(0.8, 1.2))

            # Record the event
            events.append({
                "timestamp": current_time,
                "event_type": action,
                "message": ACTION_MESSAGES.get(action, action),
                "segment_id": seg_id,
                "position": {"x": end_pos[0], "y": end_pos[1]},
                "pause_duration": pause_duration
            })

            # Animate claw for pickup/drop actions
            if action == "pickup_box":
                # Close claw
                for angle in range(0, 181, 30):
                    logs.append({
                        "timestamp": current_time,
                        "x": end_pos[0],
                        "y": end_pos[1],
                        "segment_id": seg_id,
                        "segment_index": seg_idx,
                        "section_id": section_id,
                        "checkpoint_success": 1,
                        "ultrasonic_distance": random.randint(10, 20),
                        "claw_status": angle
                    })
                    current_time += pause_duration // 6
                current_claw = 180

            elif action == "drop_box":
                # Open claw
                for angle in range(180, -1, -30):
                    logs.append({
                        "timestamp": current_time,
                        "x": end_pos[0],
                        "y": end_pos[1],
                        "segment_id": seg_id,
                        "segment_index": seg_idx,
                        "section_id": section_id,
                        "checkpoint_success": 1,
                        "ultrasonic_distance": random.randint(10, 20),
                        "claw_status": angle
                    })
                    current_time += pause_duration // 6
                current_claw = 0

            else:
                # Just pause for other actions
                current_time += pause_duration
                logs.append({
                    "timestamp": current_time,
                    "x": end_pos[0],
                    "y": end_pos[1],
                    "segment_id": seg_id,
                    "segment_index": seg_idx,
                    "section_id": section_id,
                    "checkpoint_success": 1,
                    "ultrasonic_distance": random.randint(10, 20),
                    "claw_status": current_claw
                })

        # Simulate occasional stuck behavior (poor performance)
        if random.random() < stuck_chance:
            stuck_duration = random.randint(2000, 5000)
            for _ in range(stuck_duration // 100):
                logs.append({
                    "timestamp": current_time,
                    "x": end_pos[0] + random.uniform(-2, 2),
                    "y": end_pos[1] + random.uniform(-2, 2),
                    "segment_id": seg_id,
                    "segment_index": seg_idx,
                    "section_id": section_id,
                    "checkpoint_success": 0,
                    "ultrasonic_distance": random.randint(5, 15),
                    "claw_status": current_claw
                })
                current_time += 100

            events.append({
                "timestamp": current_time - stuck_duration,
                "event_type": "stuck",
                "message": "Robot got stuck",
                "segment_id": seg_id,
                "position": {"x": end_pos[0], "y": end_pos[1]},
                "pause_duration": stuck_duration
            })

    # Add start and end events
    events.insert(0, {
        "timestamp": 0,
        "event_type": "start",
        "message": "Run Started",
        "segment_id": "s1",
        "position": {"x": 0, "y": 0},
        "pause_duration": 0
    })

    events.append({
        "timestamp": current_time,
        "event_type": "end",
        "message": "Run Completed",
        "segment_id": PATH_SEGMENTS[-1]["id"],
        "position": PATH_SEGMENTS[-1]["end"],
        "pause_duration": 0
    })

    # Sort events by timestamp
    events.sort(key=lambda x: x["timestamp"])

    return {
        "robot_id": robot_id,
        "run_number": run_number,
        "logs": logs,
        "events": events,
        "segments": segment_data,
        "metadata": {
            "duration_ms": current_time,
            "competition": f"Path Run - {performance_profile.title()} Performance",
            "notes": f"Generated path data with {len(logs)} position readings",
            "readings_count": len(logs),
            "performance_profile": performance_profile
        }
    }


# Robot configurations for test data
ROBOTS = [
    {"id": "Alpha", "runs": 4},
    {"id": "Beta", "runs": 3},
    {"id": "Gamma", "runs": 3},
]

# Performance profiles cycle through for variety
PERFORMANCE_CYCLE = ["excellent", "good", "poor", "good"]


def clear_runs():
    """Clear all runs from the database."""
    try:
        response = requests.delete(f"{API_URL}/runs/clear")
        response.raise_for_status()
        result = response.json()
        print(f"Cleared {result['deleted_count']} existing runs from database")
        return True
    except Exception as e:
        print(f"Error clearing runs: {e}")
        return False


def add_run(run_data):
    """Add a run to the database via the API."""
    try:
        response = requests.post(f"{API_URL}/ingest", json=run_data)
        response.raise_for_status()
        result = response.json()
        duration_sec = run_data['metadata']['duration_ms'] / 1000
        print(f"Added run #{run_data['run_number']} (Robot: {run_data['robot_id']})")
        print(f"  - Run ID: {result['run_id']}")
        print(f"  - Duration: {duration_sec:.1f}s")
        print(f"  - Events: {len(run_data['events'])}")
        print(f"  - Performance: {run_data['metadata']['performance_profile']}")
        return result['run_id']
    except Exception as e:
        print(f"Error adding run: {e}")
        return None


if __name__ == "__main__":
    print("Adding sample path data to MongoDB...\n")
    print("Data includes:")
    print("  - x,y position data for path animation")
    print("  - Segment traversal times")
    print("  - Events: pickup, dropoff, shooting, obstacles")
    print("  - Claw movements")
    print()

    # Clear existing runs first to avoid duplicates
    clear_runs()
    print()

    total_runs = 0
    for robot in ROBOTS:
        robot_id = robot["id"]
        num_runs = robot["runs"]
        print(f"--- Robot: {robot_id} ---")

        for run_num in range(1, num_runs + 1):
            # Cycle through performance profiles
            performance = PERFORMANCE_CYCLE[(run_num - 1) % len(PERFORMANCE_CYCLE)]
            run_data = generate_realistic_run(robot_id, run_num, performance)
            add_run(run_data)
            total_runs += 1
        print()

    print(f"\nSuccessfully added {total_runs} test runs across {len(ROBOTS)} robots!")
    print(f"\nYou can now:")
    print(f"  1. Visit http://localhost:5173/data to view the runs")
    print(f"  2. Click on any run to see the path animation")
    print(f"  3. The animation will use actual recorded timings")
