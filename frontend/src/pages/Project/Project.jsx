import { useState, useEffect } from "react"
import { getProjects, createProject, getAllDeployments, latestByProject } from "../../api/projects"
import { ProjectCard } from "../../components/ProjectCard/ProjectCard"
import { Navbar } from "../../components/Navbar/Navbar"
import "./Project.css"

function Projects() {
    const [name, setName] = useState("")
    const [description, setDescription] = useState("")
    const [projects, setProjects] = useState([])
    const [latest, setLatest] = useState({})
    const [loading, setLoading] = useState(true)
    const [creating, setCreating] = useState(false)
    const [error, setError] = useState("")

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

    async function handleSubmit(event) {
        event.preventDefault()

        try {
            setError("")
            setCreating(true)

            const data = await createProject(name.trim(), description.trim())

            // The API lists newest first, so keep the new project at the top
            setProjects((currentProjects) => [
                data,
                ...currentProjects
            ])

            setName("")
            setDescription("")
        } catch (error) {
            setError(error.message)
        } finally {
            setCreating(false)
        }
    }

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
                        <p>Give it a name; you can deploy it right after.</p>
                    </div>

                    <form
                        className="projects-form"
                        onSubmit={handleSubmit}
                    >
                        <label className="field">
                            <span className="field-label">Name</span>
                            <input
                                className="input"
                                type="text"
                                value={name}
                                onChange={(event) =>
                                    setName(event.target.value)
                                }
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

                        <button
                            className="btn btn-primary projects-create-button"
                            type="submit"
                            disabled={creating || !name.trim()}
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
