import { useState, useEffect } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { getProjectDetails, createDeployment, deleteProject, getDeployments } from "../../api/projects"
import { getUser } from "../../api/user"
import { connectGitHub } from "../../api/auth"
import { formatDateTime, shortSha, timeAgo } from "../../utils/time"
import { isInProgress } from "../../utils/deployment"
import { usePolling } from "../../hooks/usePolling"
import { DeploymentCard } from "../../components/DeploymentCard/DeploymentCard"
import { StatusBadge } from "../../components/StatusBadge/StatusBadge"
import { Navbar } from "../../components/Navbar/Navbar"
import "./ProjectDetails.css"



function ProjectDetails() {
    const [projectDetails, setProjectDetails] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [deploying, setDeploying] = useState(false)
    const [deploymentHistory, setDeploymentHistory] = useState([])
    const [historyLoading, setHistoryLoading] = useState(true)
    // null until /auth/me answers; Google-only users must connect GitHub to deploy
    const [githubConnected, setGithubConnected] = useState(null)
    const [connecting, setConnecting] = useState(false)

    const [deletingProject, setDeletingProject] = useState(false)

    const { project_id } = useParams()
    const navigate = useNavigate()

    async function handleDeleteProject() {
        const confirmed = window.confirm(
            `Delete "${projectDetails.name}"?\n\n` +
            "This stops its live site and removes all of its deployments. This cannot be undone."
        )
        if (!confirmed) return

        try {
            setDeletingProject(true)
            setError(null)
            await deleteProject(projectDetails.id)
            navigate("/projects")
        } catch (error) {
            setError(error.message)
            setDeletingProject(false)
        }
    }

    function handleDeploymentDeleted(deploymentId) {
        setDeploymentHistory((prev) => prev.filter((item) => item.id !== deploymentId))
    }

    async function handleSubmit() {
        try {
            setDeploying(true)
            setError(null)

            await createDeployment(projectDetails.id)

            await loadDeployments()
        } catch (error) {
            setError(error.message)
        } finally {
            setDeploying(false)
        }
    }

    async function handleConnectGitHub() {
        try {
            setConnecting(true)
            setError(null)
            await connectGitHub()
        } catch (error) {
            setError(error.message)
            setConnecting(false)
        }
    }

    useEffect(() => {
        getUser().then((user) => setGithubConnected(Boolean(user?.github_connected)))
    }, [])

    async function loadProjectDetails(project_id, isActive = () => true) {
        try {
            const data = await getProjectDetails(project_id)

            if(isActive()){
                setProjectDetails(data)
            }
        } catch (error) {
            if(isActive()){
                setError(
                    error.status === 404 ? "Project not found" : error.message || "Failed to load project"
                )
            }
        } finally {
            if(isActive()){
                setLoading(false)
            }
        }
    }

    async function loadDeployments(isActive = () => true) {
    try {
        const data = await getDeployments(project_id)

        if (isActive()) {
            setDeploymentHistory(data)
        }
    } catch (error) {
        if (isActive()) {
            setError(error.message || "Failed to load deployment history")
        }
    } finally {
        if (isActive()) {
            setHistoryLoading(false)
        }
    }
}

    useEffect(()=>{
        let cancelled = false
        const isActive = () => !cancelled

        setLoading(true)
        setHistoryLoading(true)
        setError(null)
        setProjectDetails(null)
        setDeploymentHistory([])

        loadProjectDetails(project_id, isActive)
        loadDeployments(isActive)

        return () => {
            cancelled = true
        }
    },[project_id])

    const hasActiveDeployment = deploymentHistory.some((item) => isInProgress(item.status))

    // Refresh the list while a deployment is queued, building or deploying
    usePolling(hasActiveDeployment, () => loadDeployments())

    // The API returns deployments newest first
    const latest = deploymentHistory[0]
    const live = deploymentHistory.find((item) => item.status === "RUNNING" && item.url)

    return (
            <div className="app-page">
                <Navbar />

                <main className="app-container">
                    <nav className="breadcrumb" aria-label="Breadcrumb">
                        <Link to="/projects">Projects</Link>
                        <span className="breadcrumb-sep">/</span>
                        <span>{projectDetails?.name ?? "…"}</span>
                    </nav>

                    <header className="page-header">
                        <div className="page-header-main">
                            <h1 className="page-title">
                                {projectDetails?.name || (loading ? "Loading…" : "Project")}
                            </h1>
                            {projectDetails && (
                                <p className="page-subtitle">
                                    {projectDetails.description || "No description provided."}
                                </p>
                            )}
                        </div>

                        {projectDetails && (
                            <div className="page-actions">
                                <button
                                    className="btn btn-primary"
                                    onClick={handleSubmit}
                                    disabled={deploying || !githubConnected}
                                    title={githubConnected === false ? "Connect GitHub to deploy" : undefined}
                                >
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                                        <path d="M12 19V5M5 12l7-7 7 7" />
                                    </svg>
                                    {deploying ? "Deploying…" : "Deploy"}
                                </button>
                                <button
                                    className="btn btn-danger"
                                    onClick={handleDeleteProject}
                                    disabled={deletingProject || hasActiveDeployment}
                                    title={hasActiveDeployment ? "Wait for the current deployment to finish" : undefined}
                                >
                                    {deletingProject ? "Deleting…" : "Delete project"}
                                </button>
                            </div>
                        )}
                    </header>

                    {githubConnected === false && (
                        <div className="alert alert-info">
                            <span>Connect your GitHub account to deploy this project.</span>
                            <button
                                className="btn btn-secondary btn-sm"
                                onClick={handleConnectGitHub}
                                disabled={connecting}
                            >
                                {connecting ? "Redirecting…" : "Connect GitHub"}
                            </button>
                        </div>
                    )}

                    {error && <div className="alert alert-error">{error}</div>}

                    {loading && <div className="loading-state">Loading project…</div>}

                    {projectDetails && (
                        <>
                            <section className="section card project-summary" aria-label="Production">
                                <div className="project-summary-item">
                                    <span className="project-summary-label">Status</span>
                                    <StatusBadge status={latest?.status} />
                                </div>
                                <div className="project-summary-item project-summary-live">
                                    <span className="project-summary-label">Live URL</span>
                                    {live ? (
                                        <a
                                            className="project-summary-value project-summary-repo"
                                            href={live.url}
                                            target="_blank"
                                            rel="noreferrer"
                                        >
                                            {live.url}
                                        </a>
                                    ) : (
                                        <span className="project-summary-value project-summary-muted">Not deployed</span>
                                    )}
                                </div>
                                <div className="project-summary-item">
                                    <span className="project-summary-label">Latest commit</span>
                                    <code className="project-summary-value">
                                        {latest ? shortSha(latest.commit_sha) : "—"}
                                    </code>
                                </div>
                                <div className="project-summary-item">
                                    <span className="project-summary-label">Last deployed</span>
                                    <span
                                        className="project-summary-value"
                                        title={latest ? formatDateTime(latest.created_at) : undefined}
                                    >
                                        {latest ? timeAgo(latest.created_at) : "Never"}
                                    </span>
                                </div>
                                <div className="project-summary-item project-summary-repository">
                                    <span className="project-summary-label">Repository</span>
                                    {projectDetails.repo_full_name ? (
                                        <a
                                            className="project-summary-value project-summary-repo"
                                            href={projectDetails.repo_html_url}
                                            target="_blank"
                                            rel="noreferrer"
                                        >
                                            {projectDetails.repo_full_name}
                                            {projectDetails.repo_private && <span className="project-summary-badge">Private</span>}
                                        </a>
                                    ) : (
                                        <span className="project-summary-value project-summary-muted">Not connected</span>
                                    )}
                                </div>
                                <div className="project-summary-item project-summary-branch">
                                    <span className="project-summary-label">Branch</span>
                                    {projectDetails.repo_branch ? (
                                        <code className="project-summary-value">{projectDetails.repo_branch}</code>
                                    ) : (
                                        <span className="project-summary-value project-summary-muted">—</span>
                                    )}
                                </div>
                            </section>

                            <section className="section">
                                <div className="section-header">
                                    <h2 className="section-title">Deployments</h2>
                                    <span className="section-meta">
                                        {deploymentHistory.length} total
                                    </span>
                                </div>

                                {historyLoading ? (
                                    <div className="loading-state">Loading deployment history…</div>
                                ) : deploymentHistory.length === 0 ? (
                                    <div className="empty-state">
                                        <h3>No deployments yet</h3>
                                        <p>Deploy this project to create your first deployment.</p>
                                    </div>
                                ) : (
                                    <ul className="card deployment-list">
                                        {deploymentHistory.map((item) => (
                                            <DeploymentCard
                                                key={item.id}
                                                deployment={item}
                                                onDeleted={handleDeploymentDeleted}
                                            />
                                        ))}
                                    </ul>
                                )}
                            </section>
                        </>
                    )}
                </main>
            </div>
        )
}

export default ProjectDetails
