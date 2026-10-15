import { useState, useEffect, useRef } from "react"
import { getProjects, createProject, getAllDeployments, latestByProject } from "../../api/projects"
import { getBranches } from "../../api/github"
import { ProjectCard } from "../../components/ProjectCard/ProjectCard"
import { RepoPicker } from "../../components/RepoPicker/RepoPicker"
import { Navbar } from "../../components/Navbar/Navbar"
import { isInProgress } from "../../utils/deployment"
import { usePolling } from "../../hooks/usePolling"
import "./Project.css"

function Projects() {
    const [name, setName] = useState("")
    const [nameEdited, setNameEdited] = useState(false)
    const [description, setDescription] = useState("")
    const [projects, setProjects] = useState([])
    const [latest, setLatest] = useState({})
    const [loading, setLoading] = useState(true)
    const [creating, setCreating] = useState(false)
    const [error, setError] = useState("")

    const [selectedRepo, setSelectedRepo] = useState(null)
    const [branches, setBranches] = useState([])
    const [branch, setBranch] = useState("")
    const [branchesLoading, setBranchesLoading] = useState(false)
    const pendingRepo = useRef(null)

    useEffect(() => {
        async function loadProjects() {
            try {
                const [projectData, deploymentData] = await Promise.all([
                    getProjects(),
                    getAllDeployments(),
                ])
                setProjects(projectData)
                setLatest(latestByProject(deploymentData))
            } catch (error) {
                setError(error.message)
            } finally {
                setLoading(false)
            }
        }

        loadProjects()
    }, [])

    // Keep project statuses live while any deployment is in progress
    usePolling(
        Object.values(latest).some((deployment) => isInProgress(deployment.status)),
        () => getAllDeployments()
            .then((deploymentData) => setLatest(latestByProject(deploymentData)))
            .catch(() => {})
    )

    async function handleSelectRepo(repo) {
        setSelectedRepo(repo)
        setBranches([])
        setBranch(repo?.default_branch ?? "")
        if (!nameEdited) setName(repo?.name ?? "")

        pendingRepo.current = repo?.full_name ?? null
        if (!repo) return

        setBranchesLoading(true)
        try {
            const data = await getBranches(repo.full_name)
            if (pendingRepo.current === repo.full_name) setBranches(data)
        } catch (error) {
            if (pendingRepo.current === repo.full_name) setError(error.message)
        } finally {
            if (pendingRepo.current === repo.full_name) setBranchesLoading(false)
        }
    }

    async function handleSubmit(event) {
        event.preventDefault()

        try {
            setError("")
            setCreating(true)

            const data = await createProject(
                name.trim(),
                description.trim(),
                selectedRepo?.full_name ?? null,
                selectedRepo ? branch : null
            )

            // The API lists newest first, so keep the new project at the top
            setProjects((currentProjects) => [
                data,
                ...currentProjects
            ])

            setName("")
            setNameEdited(false)
            setDescription("")
            handleSelectRepo(null)
        } catch (error) {
            setError(error.message)
        } finally {
            setCreating(false)
        }
    }


    const branchOptions = branches.length > 0 ? branches : branch ? [branch] : []

    return (
        <div className="app-page">
            <Navbar />

            <main className="app-container">
                <header className="page-header">
                    <div className="page-header-main">
                        <p className="eyebrow">Projects</p>
                        <h1 className="page-title">Your projects</h1>
                        <p className="page-subtitle">
                            Create and manage the applications you want to deploy.
                        </p>
                    </div>
                </header>

                <section className="section card projects-create">
                    <div className="projects-create-heading">
                        <h2 className="section-title">New project</h2>
                        <p>Import a GitHub repository, or start with just a name.</p>
                    </div>

                    <RepoPicker selected={selectedRepo} onSelect={handleSelectRepo} />

                    <form
                        className={`projects-form ${selectedRepo ? "projects-form-with-branch" : ""}`}
                        onSubmit={handleSubmit}
                    >
                        <label className="field">
                            <span className="field-label">Name</span>
                            <input
                                className="input"
                                type="text"
                                value={name}
                                onChange={(event) => {
                                    setName(event.target.value)
                                    setNameEdited(event.target.value !== "")
                                }}
                                placeholder="my-project"
                                maxLength={100}
                                required
                            />
                        </label>

                        <label className="field">
                            <span className="field-label">
                                Description <span className="field-optional">optional</span>
                            </span>
                            <input
                                className="input"
                                type="text"
                                value={description}
                                onChange={(event) =>
                                    setDescription(event.target.value)
                                }
                                placeholder="A short description"
                            />
                        </label>

                        {selectedRepo && (
                            <label className="field">
                                <span className="field-label">Branch</span>
                                <select
                                    className="input"
                                    value={branch}
                                    onChange={(event) => setBranch(event.target.value)}
                                    disabled={branchesLoading}
                                >
                                    {branchOptions.map((branchName) => (
                                        <option key={branchName} value={branchName}>
                                            {branchName}
                                            {branchName === selectedRepo.default_branch ? " (default)" : ""}
                                        </option>
                                    ))}
                                </select>
                            </label>
                        )}

                        <button
                            className="btn btn-primary projects-create-button"
                            type="submit"
                            disabled={creating || !name.trim() || (selectedRepo && !branch)}
                        >
                            {creating ? "Creating…" : "Create Project"}
                        </button>
                    </form>

                    {error && (
                        <div className="alert alert-error projects-error">
                            {error}
                        </div>
                    )}
                </section>

                <section className="section">
                    <div className="section-header">
                        <h2 className="section-title">All projects</h2>
                        <span className="section-meta">
                            {projects.length} {projects.length === 1 ? "project" : "projects"}
                        </span>
                    </div>

                    {loading ? (
                        <div className="loading-state">Loading projects…</div>
                    ) : projects.length === 0 ? (
                        <div className="empty-state">
                            <h3>No projects yet</h3>
                            <p>Create your first project above to start shipping.</p>
                        </div>
                    ) : (
                        <div className="projects-grid">
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
            </main>
        </div>
    )
}

export default Projects
