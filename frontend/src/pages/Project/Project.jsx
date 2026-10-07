import { useState, useEffect } from "react"
import { getProjects, createProject } from "../../api/projects"
import { ProjectCard } from "../../components/ProjectCard/ProjectCard"
import { Navbar } from "../../components/Navbar/Navbar"
import "./Project.css"

function Projects() {
    const [name, setName] = useState("")
    const [description, setDescription] = useState("")
    const [projects, setProjects] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState("")

    useEffect(() => {
        async function loadProjects() {
            try {
                const data = await getProjects()
                setProjects(data)
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

            const data = await createProject(name, description)

            setProjects((currentProjects) => [
                ...currentProjects,
                data
            ])

            setName("")
            setDescription("")
        } catch (error) {
            setError(error.message)
        }
    }

    return (
        <div className="projects-page">
            <Navbar />

            <header className="projects-header">
                <div>
                    <p className="projects-eyebrow">
                        PROJECTS
                    </p>

                    <h1>Your projects</h1>

                    <p className="projects-subtitle">
                        Create and manage the applications you want to deploy.
                    </p>
                </div>
            </header>

            <main className="projects-content">

                <section className="projects-create">

                    <div className="projects-section-heading">
                        <p className="projects-label">
                            NEW PROJECT
                        </p>

                        <h2>Create a project</h2>
                    </div>

                    <form
                        className="projects-form"
                        onSubmit={handleSubmit}
                    >
                        <div className="projects-field">
                            <label htmlFor="project-name">
                                Name
                            </label>

                            <input
                                id="project-name"
                                type="text"
                                value={name}
                                onChange={(event) =>
                                    setName(event.target.value)
                                }
                                placeholder="my-project"
                                required
                            />
                        </div>

                        <div className="projects-field">
                            <label htmlFor="project-description">
                                Description
                            </label>

                            <input
                                id="project-description"
                                type="text"
                                value={description}
                                onChange={(event) =>
                                    setDescription(event.target.value)
                                }
                                placeholder="A short description"
                            />
                        </div>

                        <button
                            className="projects-create-button"
                            type="submit"
                        >
                            Create Project
                        </button>
                    </form>

                    {error && (
                        <p className="projects-error">
                            {error}
                        </p>
                    )}

                </section>

                <section className="projects-list">

                    <div className="projects-section-header">
                        <div>
                            <p className="projects-label">
                                YOUR PROJECTS
                            </p>

                            <h2>Projects</h2>
                        </div>

                        <span className="projects-count">
                            {projects.length} projects
                        </span>
                    </div>

                    {loading ? (
                        <div className="projects-state">
                            Loading projects...
                        </div>
                    ) : projects.length === 0 ? (
                        <div className="projects-empty">
                            <h3>No projects yet</h3>

                            <p>
                                Create your first project to start shipping.
                            </p>
                        </div>
                    ) : (
                        <div className="projects-grid">
                            {projects.map((project) => (
                                <ProjectCard
                                    key={project.id}
                                    project={project}
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