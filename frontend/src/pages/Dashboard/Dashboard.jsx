import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { getProjects, getAllDeployments, latestByProject } from "../../api/projects"
import { ProjectCard } from "../../components/ProjectCard/ProjectCard"
import { StatusBadge } from "../../components/StatusBadge/StatusBadge"
import { Navbar } from "../../components/Navbar/Navbar"
import { shortSha, timeAgo, formatDateTime } from "../../utils/time"
import { isInProgress } from "../../utils/deployment"
import { usePolling } from "../../hooks/usePolling"
import "./Dashboard.css"

const RECENT_LIMIT = 6

function Dashboard() {
    const [projects, setProjects] = useState([])
    const [deployments, setDeployments] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState("")

    useEffect(() => {
        Promise.all([getProjects(), getAllDeployments()])
            .then(([projectData, deploymentData]) => {
                setProjects(projectData)
                setDeployments(deploymentData)
            })
            .catch((error) => setError(error.message))
            .finally(() => setLoading(false))
    }, [])

    // Keep statuses live while anything is still deploying
    usePolling(
        deployments.some((deployment) => isInProgress(deployment.status)),
        () => getAllDeployments().then(setDeployments).catch(() => {})
    )

    const latest = latestByProject(deployments)
    const latestStatuses = Object.values(latest).map((deployment) => deployment.status)
    const projectNames = Object.fromEntries(projects.map((project) => [project.id, project.name]))

    const stats = [
        { label: "Projects", value: projects.length },
        { label: "Deployments", value: deployments.length },
        { label: "Running", value: latestStatuses.filter((s) => s === "RUNNING").length, tone: "running" },
        { label: "Failing", value: latestStatuses.filter((s) => s === "FAILED").length, tone: "failed" },
    ]

    return (
        <div className="app-page">
            <Navbar />

            <main className="app-container">
                <header className="page-header">
                    <div className="page-header-main">
                        <p className="eyebrow">Overview</p>
                        <h1 className="page-title">Dashboard</h1>
                        <p className="page-subtitle">
                            Your projects and their latest deployments at a glance.
                        </p>
                    </div>

                    <div className="page-actions">
                        <Link className="btn btn-primary" to="/projects">
                            <span aria-hidden="true">+</span>
                            New Project
                        </Link>
                    </div>
                </header>

                {error && <div className="alert alert-error">{error}</div>}

                {loading ? (
                    <div className="loading-state">Loading dashboard…</div>
                ) : (
                    <>
                        <section className="section stat-grid" aria-label="Summary">
                            {stats.map((stat) => (
                                <div className="stat" key={stat.label}>
                                    <p className="stat-label">{stat.label}</p>
                                    <p className={`stat-value ${stat.value && stat.tone ? `stat-value-${stat.tone}` : ""}`}>
                                        {stat.value}
                                    </p>
                                </div>
                            ))}
                        </section>

                        <section className="section">
                            <div className="section-header">
                                <h2 className="section-title">Projects</h2>
                                <Link className="dashboard-link" to="/projects">View all →</Link>
                            </div>

                            {projects.length === 0 ? (
                                <div className="empty-state">
                                    <div className="dashboard-empty-orbit" aria-hidden="true"><span /></div>
                                    <h3>No projects yet</h3>
                                    <p>Create your first project and ship it into orbit.</p>
                                    <Link className="btn btn-primary" to="/projects">Create Project</Link>
                                </div>
                            ) : (
                                <div className="dashboard-projects">
                                    {projects.map((project) => (
                                        <ProjectCard
                                            key={project.id}
                                            project={project}
                                            latestDeployment={latest[project.id]}
                                        />
                                    ))}
                                </div>
                            )}
                        </section>

                        {deployments.length > 0 && (
                            <section className="section">
                                <div className="section-header">
                                    <h2 className="section-title">Recent deployments</h2>
                                    <span className="section-meta">
                                        last {Math.min(RECENT_LIMIT, deployments.length)}
                                    </span>
                                </div>

                                <ul className="card activity-list">
                                    {deployments.slice(0, RECENT_LIMIT).map((deployment) => (
                                        <li key={deployment.id}>
                                            <Link className="activity-row" to={`/deployments/${deployment.id}`}>
                                                <StatusBadge status={deployment.status} />
                                                <span className="activity-project">
                                                    {projectNames[deployment.project_id] ?? `Project #${deployment.project_id}`}
                                                </span>
                                                <code className="activity-sha">{shortSha(deployment.commit_sha)}</code>
                                                <time
                                                    className="activity-time"
                                                    title={formatDateTime(deployment.created_at)}
                                                >
                                                    {timeAgo(deployment.created_at)}
                                                </time>
                                            </Link>
                                        </li>
                                    ))}
                                </ul>
                            </section>
                        )}
                    </>
                )}
            </main>
        </div>
    )
}

export default Dashboard
