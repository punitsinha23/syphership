import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { getProjects } from "../../api/projects"
import { getUser } from "../../api/user"
import { ProjectCard } from "../../components/ProjectCard"
import { Navbar } from "../../components/Navbar"
import "./Dashboard.css"

function Dashboard() {
    const [user, setUser] = useState(null)
    const [projects, setProjects] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState("")

    const navigate = useNavigate()

    useEffect(() => {
        async function loadDashboard() {
            try {
                const userData = await getUser()

                if (!userData) {
                    navigate("/login")
                    return
                }

                setUser(userData)

                const data = await getProjects()
                setProjects(data)

            } catch (error) {
                console.log(error)
                setError(error.message)
            } finally {
                setLoading(false)
            }
        }

        loadDashboard()
    }, [navigate])

    if (loading) {
        return (
            <div className="dashboard-state">
                <p>Loading dashboard...</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="dashboard-state dashboard-error">
                <p>{error}</p>
            </div>
        )
    }

    return (
        <div className="dashboard">
            <Navbar />

            <main className="dashboard-main">

                <header className="dashboard-header">
                    <div>
                        <p className="dashboard-eyebrow">
                            CONTROL CENTER
                        </p>

                        <h1>Dashboard</h1>

                        <p className="dashboard-subtitle">
                            Manage your projects and deployments.
                        </p>
                    </div>

                    <button
                        className="dashboard-primary-button"
                        onClick={() => navigate("/projects")}
                    >
                        <span>+</span>
                        New Project
                    </button>
                </header>

                <section className="dashboard-content">

                    <div className="dashboard-section-header">
                        <div>
                            <p className="dashboard-section-label">
                                PROJECTS
                            </p>

                            <h2>Your projects</h2>
                        </div>

                        <span className="dashboard-project-count">
                            {projects.length} projects
                        </span>
                    </div>

                    {projects.length === 0 ? (
                        <div className="dashboard-empty">
                            <div className="dashboard-empty-orbit">
                                <span />
                            </div>

                            <h3>No projects yet</h3>

                            <p>
                                Create your first project and start shipping.
                            </p>

                            <button
                                className="dashboard-primary-button"
                                onClick={() => navigate("/projects")}
                            >
                                Create Project
                            </button>
                        </div>
                    ) : (
                        <div className="dashboard-projects">
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

export default Dashboard