import React, { useState, useEffect, useRef } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

/**
 * PathAnimator Component
 *
 * Renders and animates a robot traversing a predetermined path.
 * - Robot icon appears after a short delay
 * - Draws the path behind the robot in real-time
 * - Each segment is drawn sequentially based on its duration
 * - Path data is fetched from Flask backend or passed as props
 *
 * @param {string} runId - Optional run ID to fetch path data from specific run
 * @param {boolean} compact - If true, renders a smaller compact version
 */
function PathAnimator({ runId = null, compact = false }) {
  const [segments, setSegments] = useState([]);
  const [events, setEvents] = useState([]);
  const [isAnimating, setIsAnimating] = useState(false);
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState(-1);
  const [currentTime, setCurrentTime] = useState(0);
  const [error, setError] = useState(null);
  const [pauseText, setPauseText] = useState({ show: false, message: '', timeRemaining: 0 });
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [completedPauses, setCompletedPauses] = useState([]);
  const [showTimeline, setShowTimeline] = useState(true);

  const svgRef = useRef(null);
  const animationRef = useRef(null);
  const robotRef = useRef(null);
  const segmentStartTimeRef = useRef(0);
  const pauseTimeoutRef = useRef(null);
  const pauseStartTimeRef = useRef(0);
  const countdownIntervalRef = useRef(null);

  // Fetch path data from Flask backend
  useEffect(() => {
    fetchPathData();
    // Cleanup timers/raf on unmount
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      if (pauseTimeoutRef.current) clearTimeout(pauseTimeoutRef.current);
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  const fetchPathData = async () => {
    try {
      const url = runId ? `${API_URL}/api/path/${runId}` : `${API_URL}/api/path`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch path data');
      const data = await response.json();
      setSegments(data.segments);
      setEvents(data.events || []);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  };

  // Format time in seconds
  const formatTime = (ms) => {
    const seconds = ms / 1000;
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = (seconds % 60).toFixed(0);
    return `${minutes}m ${remainingSeconds}s`;
  };

  // Calculate total duration from segments
  const getTotalDuration = () => {
    return segments.reduce((total, seg) => {
      return total + (seg.duration || 0) + (seg.pause_duration || 0);
    }, 0);
  };

  // Calculate SVG viewBox to fit all segments
  const calculateViewBox = (segs) => {
    if (!segs || segs.length === 0) return "0 0 200 200";

    let minX = Infinity, minY = Infinity;
    let maxX = -Infinity, maxY = -Infinity;
    const SCALE_X = 1.5;

    segs.forEach(seg => {
      seg.points.forEach(([x, y]) => {
        minX = Math.min(minX, SCALE_X * x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, SCALE_X * x);
        maxY = Math.max(maxY, y);
      });
    });

    const width = maxX - minX;
    const height = maxY - minY;

    const effectiveWidth = Math.max(width, 10);
    const effectiveHeight = Math.max(height, 10);
    const padding = 5;

    return `${minX - padding} ${minY - padding} ${effectiveWidth + 2 * padding} ${effectiveHeight + 2 * padding}`;
  };

  // Calculate elapsed animation time up to a segment
  const getElapsedTimeAtSegment = (segmentIndex) => {
    let elapsed = 0;
    for (let i = 0; i < segmentIndex && i < segments.length; i++) {
      elapsed += (segments[i].duration || 0) + (segments[i].pause_duration || 0);
    }
    return elapsed;
  };

  // Start the animation
  const startAnimation = () => {
    if (segments.length === 0) return;

    resetAnimation();
    setIsAnimating(true);
    setCurrentSegmentIndex(0);
    setCurrentTime(0);

    // Delay before starting (300-500ms)
    setTimeout(() => {
      segmentStartTimeRef.current = performance.now();
      animateSegment(0, segmentStartTimeRef.current);
    }, 400);
  };

  // Animate a single segment
  const animateSegment = (segmentIndex, startTime) => {
    if (segmentIndex >= segments.length) {
      setIsAnimating(false);
      // Set final time as total duration
      setCurrentTime(getTotalDuration());
      return;
    }

    const segment = segments[segmentIndex];
    const pathElement = document.getElementById(`path-${segment.id}`);

    if (!pathElement) {
      setCurrentSegmentIndex(segmentIndex + 1);
      segmentStartTimeRef.current = performance.now();
      animateSegment(segmentIndex + 1, segmentStartTimeRef.current);
      return;
    }

    const pathLength = pathElement.getTotalLength();
    const duration = (segment.duration || 1000) / playbackSpeed;

    const animate = (frameTime) => {
      const elapsed = frameTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // Update current animation time
      const segmentElapsedTime = getElapsedTimeAtSegment(segmentIndex);
      const currentSegmentTime = (segment.duration || 0) * progress;
      setCurrentTime(segmentElapsedTime + currentSegmentTime);

      // Animate the path drawing
      const drawLength = pathLength * progress;
      pathElement.style.strokeDashoffset = pathLength - drawLength;

      // Update robot position (slightly ahead of the line)
      if (robotRef.current) {
        robotRef.current.style.opacity = '1';
        const [x1, y1] = segment.points[0];
        const [x2, y2] = segment.points[1];
        // Position ball slightly ahead of the line (5% ahead, capped at 100%)
        const leadProgress = Math.min(progress + 0.05, 1);
        // Apply 1.5x scale to match the line scaling
        const x = 1.5 * (x1 + (x2 - x1) * leadProgress);
        const y = y1 + (y2 - y1) * leadProgress;
        robotRef.current.setAttribute('cx', x);
        robotRef.current.setAttribute('cy', y);
      }

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        // Segment complete, check for pause
        if (segment.pause_duration && segment.pause_duration > 0) {
          const pauseDuration = segment.pause_duration / playbackSpeed;
          const originalPauseDuration = segment.pause_duration;
          const baseTime = segmentElapsedTime + (segment.duration || 0);

          setPauseText({
            show: true,
            message: segment.pause_message || 'Paused',
            timeRemaining: pauseDuration
          });

          // Countdown timer for pause - also updates currentTime
          pauseStartTimeRef.current = performance.now();
          countdownIntervalRef.current = setInterval(() => {
            const elapsed = performance.now() - pauseStartTimeRef.current;
            const remaining = Math.max(0, pauseDuration - elapsed);
            setPauseText(prev => ({ ...prev, timeRemaining: remaining }));

            // Update currentTime to include pause progress (in original timeline scale)
            const pauseProgress = Math.min(elapsed / pauseDuration, 1);
            const pauseTime = originalPauseDuration * pauseProgress;
            setCurrentTime(baseTime + pauseTime);
          }, 50);

          // Continue after pause
          pauseTimeoutRef.current = setTimeout(() => {
            if (countdownIntervalRef.current) {
              clearInterval(countdownIntervalRef.current);
            }
            // Set final time including full pause duration
            setCurrentTime(baseTime + originalPauseDuration);
            setPauseText({ show: false, message: '', timeRemaining: 0 });
            setCompletedPauses(prev => [...prev, segmentIndex]);

            // Move to next segment
            setCurrentSegmentIndex(segmentIndex + 1);
            segmentStartTimeRef.current = performance.now();
            animateSegment(segmentIndex + 1, segmentStartTimeRef.current);
          }, pauseDuration);
        } else {
          // No pause, move to next segment
          setCurrentSegmentIndex(segmentIndex + 1);
          segmentStartTimeRef.current = performance.now();
          animateSegment(segmentIndex + 1, segmentStartTimeRef.current);
        }
      }
    };

    animationRef.current = requestAnimationFrame(animate);
  };

  // Reset animation to initial state
  const resetAnimation = () => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    if (pauseTimeoutRef.current) {
      clearTimeout(pauseTimeoutRef.current);
    }
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
    }

    setIsAnimating(false);
    setCurrentSegmentIndex(-1);
    setCurrentTime(0);
    setPauseText({ show: false, message: '', timeRemaining: 0 });
    setCompletedPauses([]);

    // Reset all path segments
    segments.forEach(seg => {
      const pathElement = document.getElementById(`path-${seg.id}`);
      if (pathElement) {
        const length = pathElement.getTotalLength();
        pathElement.style.strokeDasharray = length;
        pathElement.style.strokeDashoffset = length;
      }
    });

    // Hide robot
    if (robotRef.current) {
      robotRef.current.style.opacity = '0';
    }
  };

  if (error) {
    return (
      <div className="container">
        <h1>Path Animator</h1>
        <div className="error">Error: {error}</div>
      </div>
    );
  }

  if (segments.length === 0) {
    return (
      <div className="container">
        <h1>Path Animator</h1>
        <p>Loading path data...</p>
      </div>
    );
  }

  return (
    <div className={compact ? "compact-animator" : "container"}>
      {!compact && <h1>Robot Path Animator</h1>}

      <div className="animator-controls">
        <button
          onClick={startAnimation}
          disabled={isAnimating}
          className="control-button"
        >
          Start Animation
        </button>
        <button
          onClick={resetAnimation}
          className="control-button"
        >
          Reset
        </button>

        <div className="speed-controls">
          <span className="speed-label">Speed:</span>
          {(compact ? [1, 2, 5, 10] : [1, 1.5, 2, 3]).map(speed => (
            <button
              key={speed}
              onClick={() => setPlaybackSpeed(speed)}
              className={`speed-button ${playbackSpeed === speed ? 'active' : ''}`}
              disabled={isAnimating}
            >
              {speed}x
            </button>
          ))}
        </div>
      </div>

      <div className="path-info">
        <p>Total Segments: {segments.length} | Duration: {formatTime(getTotalDuration())}</p>
        {isAnimating && currentSegmentIndex >= 0 && (
          <p>Segment {currentSegmentIndex + 1}/{segments.length} | Time: {formatTime(currentTime)}</p>
        )}
        <p>Playback Speed: {playbackSpeed}x</p>
      </div>

      <div className="animator-layout">
        {/* Events Timeline */}
        {events.length > 0 && showTimeline && (
          <div className="events-timeline">
            <div className="timeline-header">
              <h4>Event Timeline</h4>
              <button
                onClick={() => setShowTimeline(!showTimeline)}
                className="collapse-button"
              >
                −
              </button>
            </div>
            <div className="timeline-list">
              {events.map((event, idx) => {
                const isPast = currentTime >= event.timestamp;
                const isCurrent = isAnimating &&
                  currentTime >= event.timestamp &&
                  (idx === events.length - 1 || currentTime < events[idx + 1]?.timestamp);

                return (
                  <div
                    key={idx}
                    className={`timeline-item ${isPast ? 'past' : ''} ${isCurrent ? 'current' : ''}`}
                  >
                    <span className="timeline-time">{formatTime(event.timestamp)}</span>
                    <span className="timeline-event">{event.message}</span>
                    {event.pause_duration > 0 && (
                      <span className="timeline-pause">({formatTime(event.pause_duration)})</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {events.length > 0 && !showTimeline && (
          <button
            onClick={() => setShowTimeline(true)}
            className="show-timeline-button"
          >
            Show Timeline
          </button>
        )}

        {/* Stage wrapper for animation */}
        <div className="path-stage">
        {pauseText.show && (
          <div className="pause-overlay">
            <div className="pause-message">
              {pauseText.message}
              <div className="pause-timer">
                {(pauseText.timeRemaining / 1000).toFixed(1)}s
              </div>
            </div>
          </div>
        )}

        <svg
          ref={svgRef}
          viewBox={calculateViewBox(segments)}
          className="path-canvas"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Draw all path segments */}
          {segments.map((seg) => {
            const [x1, y1] = seg.points[0];
            const [x2, y2] = seg.points[1];

            return (
              <g key={seg.id}>
                {/* Background path (not visible) */}
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke="#d0d0d0"
                  strokeWidth="0"
                  strokeLinecap="round"
                  fill="none"
                  opacity="0.5"
                />
                {/* Animated path line */}
                <line
                  id={`path-${seg.id}`}
                  x1={1.5 * x1}
                  y1={y1}
                  x2={1.5 * x2}
                  y2={y2}
                  stroke="#6fbf8f"
                  strokeWidth="15"
                  strokeLinecap="round"
                  fill="none"
                />
              </g>
            );
          })}

          {/* Robot indicator */}
          <circle
            ref={robotRef}
            r="25"
            fill="#ff6b6b"
            stroke="#fff"
            strokeWidth="3"
            style={{ opacity: 0, transition: 'opacity 0.3s' }}
          />
        </svg>
        </div>
      </div>
    </div>
  );
}

export default PathAnimator;
