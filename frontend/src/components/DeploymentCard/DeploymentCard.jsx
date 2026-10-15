import "./DeploymentCard.css"
import { useState } from "react"
import { Link } from "react-router-dom"
import { deleteDeployment } from "../../api/projects"
import { StatusBadge } from "../StatusBadge/StatusBadge"
import { formatDateTime, shortSha, timeAgo } from "../../utils/time"
import { isInProgress } from "../../utils/deployment"

// One row of a project's deployment list (rendered inside a <ul>)
export function DeploymentCard({ deployment, onDeleted }) {
    const [deleting, setDeleting] = useState(false)
    const [error, setError] = useState(null)

    const status = deployment.status

    async function handleDelete() {
        const warning = status === "RUNNING"
            ? "This deployment is live. Deleting it takes the site offline."
            : "This removes the deployment and its build logs."
        if (!window.confirm(`Delete deployment #${deployment.id}?\n\n${warning}`)) return

        try {
            setDeleting(true)
            setError(null)
            await deleteDeployment(deployment.id)
            onDeleted?.(deployment.id)
        } catch (error) {
            setError(error.message)
            setDeleting(false)
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
                    {status === "RUNNING" && deployment.url && (
                        <a
                            className="btn btn-secondary btn-sm"
                            href={deployment.url}
                            target="_blank"
                            rel="noreferrer"
                        >
                            Visit
                        </a>
                    )}
                    <Link
                        className="btn btn-ghost btn-sm"
                        to={`/deployments/${deployment.id}`}
                        aria-label={`View deployment #${deployment.id}`}
                    >
                        View
                    </Link>
                    {!isInProgress(status) && (
                        <button
                            className="btn btn-danger btn-sm"
                            onClick={handleDelete}
                            disabled={deleting}
                            aria-label={`Delete deployment #${deployment.id}`}
                        >
                            {deleting ? "Deleting…" : "Delete"}
                        </button>
                    )}
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
