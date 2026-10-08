import "./BuildLogs.css";

export default function BuildLogs({ logs = [] }) {
  return (
    <div className="build-logs">
      <div className="build-logs-header">
        <h3>Build output</h3>
        <span>{logs.length} {logs.length === 1 ? "line" : "lines"}</span>
      </div>

      {logs.length === 0 ? (
        <div className="build-logs-empty">
          <span className="build-logs-prompt">$</span>
          No build output yet. Logs will stream here once builds run.
        </div>
      ) : (
        <div className="build-logs-content">
          {logs.map((log, index) => (
            <div className="log-line" key={index}>
              <span className="log-number">{index + 1}</span>
              <span>{log}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
