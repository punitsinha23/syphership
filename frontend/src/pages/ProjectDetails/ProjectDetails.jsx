import { useState, useEffect } from "react"
import { Link, useParams } from "react-router-dom"
import { getProjectDetails, createDeployment, getDeployments } from "../../api/projects"
import { getUser } from "../../api/user"
import { connectGitHub } from "../../api/auth"
import { generateMockSha } from "../../utils/mockCommit"
import { formatDateTime, shortSha, timeAgo } from "../../utils/time"
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

    const { project_id } = useParams()

    async function handleSubmit() {
        try {
            setDeploying(true)
            setError(null)
            const commitSha = generateMockSha()

            await createDeployment(
                projectDetails.id,
                commitSha
            )

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

    function handleStatusUpdated(updatedDeployment){
        setDeploymentHistory((prev)=>
            prev.map((item) =>
                item.id === updatedDeployment.id ? updatedDeployment : item
            )
        )
    }

    // The API returns deployments newest first
    const latest = deploymentHistory[0]

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
                                <div className="project-summary-item project-summary-item-wide">
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
                                <div className="project-summary-item">
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
                                                onStatusUpdated={handleStatusUpdated}
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
