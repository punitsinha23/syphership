import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { getProjects } from "../api/projects"
import { getUser } from "../api/user"
import { ProjectCard } from "../components/ProjectCard"

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
                    navigate('/login')
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

    }, [])

    if (loading) {
        return <p>Loading...</p>
    }

    if (error) {
        return <p>{error}</p>
    }

    return (
        <div>
            <h1>Dashboard</h1>

            {user && (
                <p>Welcome, {user.username}</p>
            )}

            <h2>Projects</h2>

            {projects.length === 0 ? (
                <p>No projects yet.</p>
            ) : (
                projects.map((project) => (
                    <div key={project.id}>
                        <ProjectCard project={project}/>
                    </div>
                ))
            )}
        </div>
    )
}

export default Dashboard