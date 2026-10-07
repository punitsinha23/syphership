import "./DeploymentCard.css"
import { useState } from "react"
import { updateStatus } from "../../api/projects"
import { Link } from "react-router-dom"

const NEXT_STATUS = {
    QUEUED: "BUILDING",
    BUILDING: "DEPLOYING",
    DEPLOYING: "RUNNING"
}

export function DeploymentCard({ deployment, onStatusUpdated }) {
    const [updating, setUpdating] = useState(false)
    const [error, setError] = useState(null)

    const status = deployment.status
    const nextStatus = NEXT_STATUS[status]

    async function handleSubmit() {
        if (!nextStatus || updating) return

        try {
            setUpdating(true)
            setError(null)

            const data = await updateStatus(
                deployment.id,
                nextStatus
            )

            onStatusUpdated?.(data)
        } catch (error) {
            setError(error.message)
        } finally {
            setUpdating(false)
        }
    }

    function buttonLabel() {
        if (updating) return "Updating..."
        if (status === "RUNNING") return "Deployment complete"
        if (status === "FAILED") return "Deployment failed"
        return "Advance status"
    }

    return (
        <article className="deployment-card">

            <div className="deployment-card-main">

                <div className="deployment-card-header">
                    <div>
                        <p className="deployment-card-label">
                            DEPLOYMENT #{deployment.id}
                        </p>

                        <h2>
                            {status}
                        </h2>
                    </div>

                    <span
                        className={`deployment-status deployment-status-${status.toLowerCase()}`}
                    >
                        <span className="deployment-status-dot" />
                        {status}
                    </span>
                </div>

                <div className="deployment-card-meta">

                    <div className="deployment-meta-item">
                        <span>COMMIT</span>
                        <code>{deployment.commit_sha}</code>
                    </div>

                    <div className="deployment-meta-item">
                        <span>CREATED</span>
                        <time>
                            {new Date(
                                deployment.created_at
                            ).toLocaleString()}
                        </time>
                    </div>

                </div>

                {deployment.failure_reason && (
                    <div className="deployment-card-failure">
                        <span>Failure</span>
                        <p>{deployment.failure_reason}</p>
                    </div>
                )}

                {error && (
                    <p className="deployment-card-error">
                        {error}
                    </p>
                )}

            </div>

            <div className="deployment-card-actions">

                <button
                    className="deployment-card-button"
                    onClick={handleSubmit}
                    disabled={!nextStatus || updating}
                >
                    {buttonLabel()}
                </button>

                <Link
                    className="deployment-card-link"
                    to={`/deployments/${deployment.id}`}
                >
                    View details →
                </Link>

            </div>

        </article>
    )
}