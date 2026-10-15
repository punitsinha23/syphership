import { deleteDeployment, getDeployment, getDeploymentLogs, getProjectDetails } from "../../api/projects"
import { isInProgress } from "../../utils/deployment"
import { usePolling } from "../../hooks/usePolling"
import { useState, useEffect } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import DeploymentTimeline from "../../components/DeploymentTimeline/DeploymentTimeline"
import BuildLogs from "../../components/BuildLogs/BuildLogs"
import { Navbar } from "../../components/Navbar/Navbar"
import { StatusBadge } from "../../components/StatusBadge/StatusBadge"
import { formatDateTime, parseApiDate, shortSha, timeAgo } from "../../utils/time"
import "./DeploymentDetails.css"

function formatDuration(start, end) {
    const seconds = Math.max(0, Math.round((parseApiDate(end) - parseApiDate(start)) / 1000))
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes}m ${seconds % 60}s`
    return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
}

function DeploymentDetails() {
    const [deploymentDetails, setDeploymentDetails] = useState(null)
    const [project, setProject] = useState(null)
    const [error, setError] = useState(null)
    const [loading, setLoading] = useState(true)
    const [buildLogs, setBuildLogs] = useState(null)
    const [deleting, setDeleting] = useState(false)
    const [deleteError, setDeleteError] = useState(null)

    const { deployment_id } = useParams()
    const navigate = useNavigate()

    // Logs are optional on this page, so a failure only leaves them empty
    async function loadLogs(isActive) {
        try {
            const data = await getDeploymentLogs(deployment_id)
            if (isActive()) {
                setBuildLogs(data.build_logs)
            }
        } catch {
            // Keep whatever was shown before
        }
    }

    useEffect(() => {
            let cancelled = false

            async function loadDeployment() {
                try {
                    setLoading(true)
                    setError(null)

                    const data = await getDeployment(deployment_id)

                    if (!cancelled) {
                        setDeploymentDetails(data)
                    }

                    loadLogs(() => !cancelled)

                    // Only used for the breadcrumb, so a failure here isn't fatal
                    getProjectDetails(data.project_id)
                        .then((projectData) => !cancelled && setProject(projectData))
                        .catch(() => {})
                } catch (error) {
                    if (!cancelled) {
                        if (error.status === 404) {
                            setError("Deployment not found")
                        } else {
                            setError(error.message || "Failed to load deployment")
                        }
                    }
                } finally {
                    if (!cancelled) {
                        setLoading(false)
                    }
                }
            }

            loadDeployment()

            return () => {
                cancelled = true
            }
        }, [deployment_id])

    const inProgress = isInProgress(deploymentDetails?.status)

    // Follow the pipeline live until the deployment finishes
    usePolling(inProgress, async () => {
        try {
            setDeploymentDetails(await getDeployment(deployment_id))
            await loadLogs(() => true)
        } catch {
            // Keep showing the last known state; the next tick retries
        }
    })

    async function handleDelete() {
        const warning = deploymentDetails.status === "RUNNING"
            ? "This deployment is live. Deleting it takes the site offline."
            : "This removes the deployment and its build logs."
        if (!window.confirm(`Delete deployment #${deploymentDetails.id}?\n\n${warning}`)) return

        try {
            setDeleting(true)
            setDeleteError(null)
            await deleteDeployment(deploymentDetails.id)
            navigate(`/projects/${deploymentDetails.project_id}`)
        } catch (error) {
            setDeleteError(error.message)
            setDeleting(false)
        }
    }

    const d = deploymentDetails
    const finished = d && !inProgress

    return (
        <div className="app-page">
            <Navbar />

            <main className="app-container">
                <nav className="breadcrumb" aria-label="Breadcrumb">
                    <Link to="/projects">Projects</Link>
                    <span className="breadcrumb-sep">/</span>
                    {d ? (
                        <Link to={`/projects/${d.project_id}`}>{project?.name ?? `Project #${d.project_id}`}</Link>
                    ) : (
                        <span>…</span>
                    )}
                    <span className="breadcrumb-sep">/</span>
                    <span>#{deployment_id}</span>
                </nav>

                {loading ? (
                    <div className="loading-state">Loading deployment…</div>
                ) : error ? (
                    <div className="empty-state">
                        <h3>{error}</h3>
                        <p>It may have been deleted, or it belongs to another account.</p>
                        <Link className="btn btn-secondary" to="/projects">Back to projects</Link>
                    </div>
                ) : d && (
                    <>
                        <header className="page-header">
                            <div className="page-header-main">
                                <h1 className="page-title deployment-title">
                                    Deployment #{d.id}
                                    <StatusBadge status={d.status} />
                                </h1>
                                <p className="page-subtitle">
                                    Commit <code className="deployment-inline-sha">{shortSha(d.commit_sha)}</code>
                                    {" "}· created {timeAgo(d.created_at)}
                                </p>
                            </div>

                            {!inProgress && (
                                <div className="page-actions">
                                    <button
                                        className="btn btn-danger"
                                        onClick={handleDelete}
                                        disabled={deleting}
                                    >
                                        {deleting ? "Deleting…" : "Delete deployment"}
                                    </button>
                                </div>
                            )}
                        </header>

                        {deleteError && <div className="alert alert-error">{deleteError}</div>}

                        {d.failure_reason && (
                            <div className="alert alert-error deployment-failure">
                                <span>
                                    <strong>Failure reason</strong>
                                    {d.failure_reason}
                                </span>
                            </div>
                        )}

                        <section className="section">
                            <div className="section-header">
                                <h2 className="section-title">Pipeline</h2>
                            </div>
                            <DeploymentTimeline status={d.status} />
                        </section>

                        <section className="section card deployment-info" aria-label="Details">
                            {d.status === "RUNNING" && d.url && (
                                <div className="deployment-info-item deployment-info-wide">
                                    <span className="deployment-info-label">Live URL</span>
                                    <a
                                        className="deployment-info-value"
                                        href={d.url}
                                        target="_blank"
                                        rel="noreferrer"
                                    >
                                        {d.url}
                                    </a>
                                </div>
                            )}
                            <div className="deployment-info-item deployment-info-wide">
                                <span className="deployment-info-label">Commit SHA</span>
                                <code className="deployment-info-value">{d.commit_sha}</code>
                            </div>
                            <div className="deployment-info-item">
                                <span className="deployment-info-label">Created</span>
                                <span className="deployment-info-value">{formatDateTime(d.created_at)}</span>
                            </div>
                            <div className="deployment-info-item">
                                <span className="deployment-info-label">Last update</span>
                                <span className="deployment-info-value">{formatDateTime(d.updated_at)}</span>
                            </div>
                            <div className="deployment-info-item">
                                <span className="deployment-info-label">
                                    {finished ? "Duration" : "Elapsed"}
                                </span>
                                <span className="deployment-info-value">
                                    {formatDuration(d.created_at, finished ? d.updated_at : new Date().toISOString())}
                                </span>
                            </div>
                        </section>

                        <section className="section">
                            <BuildLogs logs={buildLogs} pending={inProgress} />
                        </section>
                    </>
                )}
            </main>
        </div>
    )
}

export default DeploymentDetails
