import { useEffect, useRef } from "react";
import "./BuildLogs.css";

// logs: the raw build output from the API (one string), or null
export default function BuildLogs({ logs = null, pending = false }) {
  const contentRef = useRef(null);
  const lines = logs ? logs.replace(/\n$/, "").split("\n") : [];

  // Build errors are at the end, so start scrolled to the bottom
  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="build-logs">
      <div className="build-logs-header">
        <h3>Build output</h3>
        <span>{lines.length} {lines.length === 1 ? "line" : "lines"}</span>
      </div>

      {lines.length === 0 ? (
        <div className="build-logs-empty">
          <span className="build-logs-prompt">$</span>
          {pending
            ? "Building… output appears here when the build finishes."
            : "No build output for this deployment."}
        </div>
      ) : (
        <div className="build-logs-content" ref={contentRef}>
          {lines.map((line, index) => (
            <div className="log-line" key={index}>
              <span className="log-number">{index + 1}</span>
              <span>{line}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
