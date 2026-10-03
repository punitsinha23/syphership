
import { useState, useEffect } from "react"
import { useParams } from "react-router-dom"
import { getProjectDetails, createDeployment } from "../api/projects"
import { ProjectCard } from "../components/ProjectCard"
import { generateMockSha } from "../utils/mockCommit"
import { getDeployments } from "../api/projects"
import { DeploymentCard } from "../components/DeploymentCard"


function ProjectDetails() {
    const [projectDetails, setProjectDetails] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [deployment, setDeployment] = useState(null)
    const [deploying, setDeploying] = useState(false)
    const [deploymentHistory, setDeploymentHistory] = useState([])

    const { project_id } = useParams()

    async function handleSubmit() {
        try {
            setDeploying(true)
            setError(null)
            const commitSha = generateMockSha()

            const data = await createDeployment(
                projectDetails.id,
                commitSha
            )

            setDeployment(data)
            await loadDeployments()
        } catch (error) {
            setError(error.message)
        } finally {
            setDeploying(false)
        }
    }

    async function loadProjectDetails(project_id) {
        try {
            const data = await getProjectDetails(project_id)
            setProjectDetails(data)
        } catch (error) {
            setError(error.message)
        } finally {
            setLoading(false)
        }
    }

    async function loadDeployments() {
        try{
            const data = await getDeployments()
            
            const filterDeployment = data.filter(
                (item) => item.project_id === Number(project_id)
            )
            setDeploymentHistory(filterDeployment)
        }catch(error){
            setError(error.message)
        }
    }

    useEffect(()=>{
        loadProjectDetails(project_id)
        loadDeployments()
    },[project_id])

    return (
        <div>
            <h1>Project details</h1>

            {loading && <p>Loading...</p>}
            {error && <p>{error}</p>}

            {projectDetails && (
                <>
                    <ProjectCard project={projectDetails} />

                    <button
                        onClick={handleSubmit}
                        disabled={deploying}
                    >
                        {deploying ? "Deploying..." : "Deploy"}
                    </button>
                </>
            )}

            {deployment && (
                <p>Deployment status: {deployment.status}</p>
            )}
            
            <h2>Deployment History</h2>

            {deploymentHistory.length === 0 ? (
                <p>No deployments yet.</p>
            ) : (
                deploymentHistory.map((item) => (
                    <div>
                        <DeploymentCard key={item.id} deployment={item}/>
                    </div>
                ))
            )}
        </div>
    )
}

export default ProjectDetails