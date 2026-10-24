import "./DeploymentTimeline.css"

const stages = [
    { key: "QUEUED", label: "Queued", hint: "Waiting for a builder" },
    { key: "BUILDING", label: "Build", hint: "Compiling the application" },
    { key: "DEPLOYING", label: "Deploy", hint: "Shipping to production" },
    { key: "RUNNING", label: "Run", hint: "Serving traffic" },
];

function stepState(index, currentIndex, status) {
  // A stopped deployment ran successfully before it was replaced
  if (status === "RUNNING" || status === "STOPPED" || index < currentIndex) return "done";
  if (index === currentIndex) return status === "FAILED" ? "error" : "active";
  return "pending";
}

export default function DeploymentTimeline({ status, failedStage }) {
  const isFailed = status === "FAILED";
  // A failed deployment is positioned at the stage it failed in
  const currentIndex = stages.findIndex((stage) => stage.key === (isFailed ? failedStage : status));
  // Deployments that failed before failed_stage existed have no known stage
  const stageUnknown = isFailed && currentIndex === -1;

  return (
    <ol className={`pipeline ${isFailed ? "pipeline-failed" : ""}`}>
      {stages.map((stage, index) => {
        const state = stageUnknown ? "unknown" : stepState(index, currentIndex, status);

        return (
          <li key={stage.key} className={`pipeline-step pipeline-step-${state}`}>
            <span className="pipeline-node" aria-hidden="true">
              {state === "done" && (
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12l5 5 9-10" />
                </svg>
              )}
              {state === "error" && (
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round">
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              )}
            </span>
            <span className="pipeline-index">0{index + 1}</span>
            <span className="pipeline-label">{stage.label}</span>
            <span className="pipeline-hint">
              {state === "active" ? "In progress" : state === "error" ? "Failed here" : stage.hint}
            </span>
          </li>
        );
      })}

      {stageUnknown && (
        <li className="pipeline-step pipeline-step-error">
          <span className="pipeline-node" aria-hidden="true">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </span>
          <span className="pipeline-index">ERR</span>
          <span className="pipeline-label">Failed</span>
          <span className="pipeline-hint">Deployment stopped</span>
        </li>
      )}

      {status === "STOPPED" && (
        <li className="pipeline-step pipeline-step-unknown">
          <span className="pipeline-node" aria-hidden="true" />
          <span className="pipeline-index">END</span>
          <span className="pipeline-label">Stopped</span>
          <span className="pipeline-hint">Replaced by a newer deployment</span>
        </li>
      )}
    </ol>
  );
}
