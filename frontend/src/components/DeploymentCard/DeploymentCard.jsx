import "./DeploymentCard.css"
import { useState } from "react"
import { updateStatus } from "../../api/projects"
import { Link } from "react-router-dom"
import { StatusBadge } from "../StatusBadge/StatusBadge"
import { formatDateTime, shortSha, timeAgo } from "../../utils/time"

const NEXT_STATUS = {
    QUEUED: "BUILDING",
    BUILDING: "DEPLOYING",
    DEPLOYING: "RUNNING"
}

// One row of a project's deployment list (rendered inside a <ul>)
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

    return (
        <li className="deployment-row">
            <div className="deployment-row-main">
                <StatusBadge status={status} />

                <Link className="deployment-row-title" to={`/deployments/${deployment.id}`}>
                    Deployment #{deployment.id}
                </Link>

                <code className="deployment-row-sha" title={deployment.commit_sha}>
                    {shortSha(deployment.commit_sha)}
                </code>

                <time
                    className="deployment-row-time"
                    title={formatDateTime(deployment.created_at)}
                >
                    {timeAgo(deployment.created_at)}
                </time>

                <div className="deployment-row-actions">
                    {nextStatus && (
                        <button
                            className="btn btn-secondary btn-sm"
                            onClick={handleSubmit}
                            disabled={updating}
                            title={`Move this deployment to ${nextStatus}`}
                        >
                            {updating ? "Updating…" : (
                                <>Advance<span className="deployment-row-next"> → {nextStatus}</span></>
                            )}
                        </button>
                    )}
                    <Link
                        className="btn btn-ghost btn-sm"
                        to={`/deployments/${deployment.id}`}
                        aria-label={`View deployment #${deployment.id}`}
                    >
                        View
                    </Link>
                </div>
            </div>

            {deployment.failure_reason && (
                <p className="deployment-row-failure">
                    {deployment.failure_reason}
                </p>
            )}

            {error && (
                <p className="deployment-row-error">
                    {error}
                </p>
            )}
        </li>
    )
}
