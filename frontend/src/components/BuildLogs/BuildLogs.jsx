import "./BuildLogs.css";

export default function BuildLogs({ logs = [] }) {
  return (
    <div className="build-logs">
      <div className="build-logs-header">
        <h3>Build Logs</h3>
        <span>{logs.length} lines</span>
      </div>

      {logs.length === 0 ? (
        <div className="build-logs-empty">
          No build logs available yet.
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