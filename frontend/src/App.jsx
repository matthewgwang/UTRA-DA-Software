import { Routes, Route, Link } from "react-router-dom";
import React, { useState, useEffect } from 'react';
import PathAnimator from './PathAnimator';
import './animator.css';

// Backend API URL (adjust if needed)
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

function Home() {
  return (
    <div className="container">
      <h1>Welcome</h1>
      <p>
        Hi, my name is <strong>Andrew</strong>.
      </p>
      <p>
        This website is a data analysis platform designed to explore, visualize,
        and interpret meaningful datasets. More features will be added over time,
        including analytics, insights, and audio narration.
      </p>
    </div>
  );
}

function Data() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRun, setSelectedRun] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    fetchRuns();
  }, []);

  const fetchRuns = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/runs`);
      if (!response.ok) throw new Error('Failed to fetch runs');
      const data = await response.json();
      setRuns(data.runs);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchRunDetails = async (runId) => {
    try {
      const response = await fetch(`${API_URL}/runs/${runId}`);
      if (!response.ok) throw new Error('Failed to fetch run details');
      const data = await response.json();
      setSelectedRun(data);
    } catch (err) {
      setError(err.message);
    }
  };

  const analyzeRun = async (runId) => {
    try {
      setAnalyzing(true);
      const response = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: runId })
      });
      if (!response.ok) throw new Error('Failed to analyze run');
      await response.json();

      // Refresh the run details to show the analysis
      await fetchRunDetails(runId);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) {
    return (
      <div className="container">
        <h1>Data</h1>
        <p>Loading runs...</p>
      </div>
    );
  }

  return (
    <div className="container">
      <h1>Robot Run Data</h1>

      {error && <div className="error">Error: {error}</div>}

      {selectedRun ? (
        <RunDetail
          run={selectedRun}
          onBack={() => setSelectedRun(null)}
          onAnalyze={analyzeRun}
          analyzing={analyzing}
        />
      ) : (
        <RunsList
          runs={runs}
          onSelectRun={fetchRunDetails}
        />
      )}
    </div>
  );
}

function RunsList({ runs, onSelectRun }) {
  if (runs.length === 0) {
    return <p>No runs found. Upload some data to get started.</p>;
  }

  // Group runs by robot_id
  const runsByRobot = runs.reduce((groups, run) => {
    const robotId = run.robot_id || 'Unknown';
    if (!groups[robotId]) {
      groups[robotId] = [];
    }
    groups[robotId].push(run);
    return groups;
  }, {});

  // Sort robots alphabetically
  const sortedRobots = Object.keys(runsByRobot).sort();

  return (
    <div className="runs-list">
      <h2>All Runs ({runs.length})</h2>

      {sortedRobots.map(robotId => (
        <div key={robotId} className="robot-group">
          <h3 className="robot-header">
            <span className="robot-icon">🤖</span>
            Robot: {robotId}
            <span className="run-count">({runsByRobot[robotId].length} runs)</span>
          </h3>
          <div className="runs-grid">
            {runsByRobot[robotId]
              .sort((a, b) => a.run_number - b.run_number)
              .map(run => (
                <div key={run._id} className="run-card" onClick={() => onSelectRun(run._id)}>
                  <div className="run-header">
                    <strong>Run #{run.run_number}</strong>
                    {run.analyzed && <span className="badge">Analyzed</span>}
                  </div>
                  <div className="run-info">
                    <div>Logs: {run.logs_count}</div>
                    <div className="run-date">
                      {new Date(run.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function RunDetail({ run, onBack, onAnalyze, analyzing }) {
  const [showAllLogs, setShowAllLogs] = useState(false);
  const [showMetrics, setShowMetrics] = useState(true);
  const logsToShow = showAllLogs ? run.logs : run.logs.slice(0, 20);

  const formatTime = (ms) => {
    return (ms / 1000).toFixed(2) + 's';
  };

  return (
    <div className="run-detail">
      <button onClick={onBack} className="back-button">← Back to All Runs</button>

      <div className="detail-header">
        <h2>Run #{run.run_number}</h2>
        <div className="detail-meta">
          <span>Robot: {run.robot_id}</span>
          <span>Created: {new Date(run.created_at).toLocaleString()}</span>
          <span>Total Events: {run.logs.length}</span>
        </div>
      </div>

      {/* Analysis Section */}
      <div className="analysis-section">
        <div className="section-header">
          <h3>Analysis</h3>
          <button
            onClick={() => onAnalyze(run._id)}
            disabled={analyzing}
            className="analyze-button"
          >
            {analyzing ? 'Analyzing...' : run.analyzed ? 'Re-analyze' : 'Analyze Run'}
          </button>
        </div>

        {run.analysis ? (
          <div className="analysis-result">
            {run.analysis.summary && (
              <div className="analysis-summary">
                <h4>Summary</h4>
                <p className="summary-text">{run.analysis.summary}</p>
              </div>
            )}

            {/* Chronological Mission Timeline */}
            {run.analysis.timeline && run.analysis.timeline.length > 0 && (
              <div className="mission-timeline">
                <h4>Mission Timeline</h4>
                <div className="timeline-list">
                  {run.analysis.timeline.map((item, idx) => (
                    <div key={idx} className="timeline-item">
                      <span className="timeline-time">{formatTime(item.time_ms)}</span>
                      <span className="timeline-event">{item.event}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(run.analysis.checkpoint_rate !== undefined || run.analysis.ultrasonic_avg !== undefined) && (
              <div className="event-summary">
                <div className="collapsible-header">
                  <h4>Performance Metrics</h4>
                  <button
                    onClick={() => setShowMetrics(!showMetrics)}
                    className="collapse-button"
                  >
                    {showMetrics ? '−' : '+'}
                  </button>
                </div>
                {showMetrics && (
                  <div className="event-grid">
                    {run.analysis.checkpoint_rate !== undefined && (
                      <div className="event-stat">
                        <span className="event-name">Checkpoint Success:</span>
                        <span className="event-count">{run.analysis.checkpoint_rate.toFixed(1)}%</span>
                      </div>
                    )}
                    {run.analysis.ultrasonic_avg !== undefined && (
                      <div className="event-stat">
                        <span className="event-name">Avg Ultrasonic:</span>
                        <span className="event-count">{run.analysis.ultrasonic_avg.toFixed(1)}cm</span>
                      </div>
                    )}
                    {run.analysis.claw_changes !== undefined && (
                      <div className="event-stat">
                        <span className="event-name">Claw Changes:</span>
                        <span className="event-count">{run.analysis.claw_changes}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {run.analysis.issues && run.analysis.issues.length > 0 && (
              <div className="issues-section">
                <h4>Issues Detected</h4>
                <ul className="issues-list">
                  {run.analysis.issues.map((issue, idx) => (
                    <li key={idx} className="issue-item">{issue}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <p className="no-analysis">No analysis available yet. Click "Analyze Run" to generate insights.</p>
        )}
      </div>

      {/* Path Animation */}
      <div className="path-animation-section">
        <h3>Path Visualization</h3>
        <PathAnimator runId={run._id} compact={true} />
      </div>

      {/* Event Logs Section */}
      <div className="logs-section">
        <h3>Sensor Readings</h3>
        <div className="logs-table-wide">
          <div className="logs-header-wide">
            <span>Time</span>
            <span>Checkpoint</span>
            <span>Ultrasonic</span>
            <span>Claw</span>
          </div>
          {logsToShow.map((log, idx) => (
            <div key={idx} className="log-row-wide">
              <span className="log-time">{formatTime(log.timestamp_ms)}</span>
              <span className={log.checkpoint_success === 1 ? "log-success" : "log-miss"}>
                {log.checkpoint_success === 1 ? '✓ Hit' : '✗ Miss'}
              </span>
              <span className="log-zone">{log.ultrasonic_distance}cm</span>
              <span className="log-zone">{log.claw_status}°</span>
            </div>
          ))}
        </div>

        {run.logs.length > 20 && (
          <button
            onClick={() => setShowAllLogs(!showAllLogs)}
            className="toggle-logs-button"
          >
            {showAllLogs ? 'Show Less' : `Show All ${run.logs.length} Logs`}
          </button>
        )}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <>
      <nav>
        <Link to="/">Home</Link>
        <Link to="/data">Data</Link>
      </nav>

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/data" element={<Data />} />
      </Routes>
    </>
  );
}
