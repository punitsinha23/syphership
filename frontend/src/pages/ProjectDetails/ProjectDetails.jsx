
import { useState, useEffect } from "react"
import { useParams } from "react-router-dom"
import { getProjectDetails, createDeployment, getDeployments } from "../../api/projects"
import { generateMockSha } from "../../utils/mockCommit"
import { DeploymentCard } from "../../components/DeploymentCard/DeploymentCard"
import { Navbar } from "../../components/Navbar"
import "./ProjectDetails.css"



function ProjectDetails() {
    const [projectDetails, setProjectDetails] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [deployment, setDeployment] = useState(null)
    const [deploying, setDeploying] = useState(false)
    const [deploymentHistory, setDeploymentHistory] = useState([])
    const [historyLoading, setHistoryLoading] = useState(true)

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
            setDeploymentHistory(
                data.filter(item => item.project_id === Number(project_id))
            )
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
        setDeployment(null)

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
        setDeployment((prev) =>
        prev?.id === updatedDeployment.id ? updatedDeployment : prev
    )
    }

    return (
            <div className="project-details">
                <Navbar />

                <header className="project-details-header">
                    <div>
                        <p className="project-details-eyebrow">
                            PROJECT
                        </p>

                        <h1>{projectDetails?.name || "Project Details"}</h1>

                        {projectDetails && (
                            <p className="project-details-description">
                                {projectDetails.description || "No description provided."}
                            </p>
                        )}
                    </div>

                    {projectDetails && (
                        <button
                            className="project-details-deploy-button"
                            onClick={handleSubmit}
                            disabled={deploying}
                        >
                            {deploying ? "Deploying..." : "Deploy"}
                        </button>
                    )}
                </header>

                {loading && (
                    <div className="project-details-state">
                        Loading project...
                    </div>
                )}

                {error && (
                    <div className="project-details-error">
                        {error}
                    </div>
                )}

                {projectDetails && (
                    <main className="project-details-content">

                        {deployment && (
                            <section className="project-details-current">
                                <div>
                                    <p className="project-details-label">
                                        LATEST DEPLOYMENT
                                    </p>

                                    <h2>Deployment #{deployment.id}</h2>
                                </div>

                                <span className="project-details-status">
                                    {deployment.status}
                                </span>
                            </section>
                        )}

                        <section className="project-details-history">
                            <div className="project-details-section-header">
                                <div>
                                    <p className="project-details-label">
                                        DEPLOYMENTS
                                    </p>

                                    <h2>Deployment History</h2>
                                </div>

                                <span className="project-details-count">
                                    {deploymentHistory.length} deployments
                                </span>
                            </div>

                            {historyLoading ? (
                                <div className="project-details-state">
                                    Loading deployment history...
                                </div>
                            ) : deploymentHistory.length === 0 ? (
                                <div className="project-details-empty">
                                    <h3>No deployments yet</h3>

                                    <p>
                                        Deploy this project to create your first deployment.
                                    </p>
                                </div>
                            ) : (
                                <div className="project-details-deployments">
                                    {deploymentHistory.map((item) => (
                                        <DeploymentCard
                                            key={item.id}
                                            deployment={item}
                                            onStatusUpdated={handleStatusUpdated}
                                        />
                                    ))}
                                </div>
                            )}
                        </section>

                    </main>
                )}

            </div>
        )
}

export default ProjectDetails