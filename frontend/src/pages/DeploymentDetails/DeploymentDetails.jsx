import { getDeployment } from "../../api/projects"
import { useState, useEffect } from "react"
import { useParams } from "react-router-dom"
import DeploymentTimeline from "../../components/DeploymentTimeline/DeploymentTimeline"
import BuildLogs from "../../components/BuildLogs/BuildLogs"
import { Navbar } from "../../components/Navbar/Navbar"
import "./DeploymentDetails.css"

function DeploymentDetails() {
    const [deploymentDetails, setDeploymentDetails] = useState(null)
    const [error, setError] = useState(null)
    const [loading, setLoading] = useState(true)

    const { deployment_id } = useParams()

    useEffect(() => {
            let cancelled = false

            async function loadDeployment() {
                try {
                    setLoading(true)
                    setError(null)

                    const data = await getDeployment(deployment_id)

                    if (!cancelled) {
                        setDeploymentDetails(data)
                    }
                } catch (error) {
                    if (!cancelled) {
                        if (error.status === 404) {
                            setError("Deployment not found")
                        } else {
                            setError(error.message || "Failed to load deployment")
                        }
                    }
                } finally {
                    if (!cancelled) {
                        setLoading(false)
                    }
                }
            }

            loadDeployment()

            return () => {
                cancelled = true
            }
        }, [deployment_id])

    if (loading) {
        return (
            <div className="deployment-details-state">
                <p>Loading deployment...</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="deployment-details-state deployment-details-error">
                <p>{error}</p>
            </div>
        )
    }

    if (!deploymentDetails) {
        return (
            <div className="deployment-details-state">
                <p>Deployment not found</p>
            </div>
        )
    }

    return (
        <div className="deployment-details">
            <Navbar />

            <header className="deployment-details-header">
                <div>
                    <p className="deployment-details-eyebrow">
                        DEPLOYMENT
                    </p>
                    <h1>Deployment #{deploymentDetails.id}</h1>
                </div>
                <span className={`deployment-status deployment-status-${deploymentDetails.status.toLowerCase()}`}>
                    <span className="deployment-status-dot" />
                    {deploymentDetails.status}
                </span>
            </header>

            <main className="deployment-details-content">
                <section className="deployment-details-info">
                    <div className="deployment-detail-item">
                        <span className="deployment-detail-label">COMMIT SHA</span>
                        <code className="deployment-detail-value">{deploymentDetails.commit_sha}</code>
                    </div>
                    <div className="deployment-detail-item">
                        <span className="deployment-detail-label">CREATED</span>
                        <span className="deployment-detail-value">
                            {new Date(deploymentDetails.created_at).toLocaleString()}
                        </span>
                    </div>
                    <div className="deployment-detail-item">
                        <span className="deployment-detail-label">UPDATED</span>
                        <span className="deployment-detail-value">
                            {new Date(deploymentDetails.updated_at).toLocaleString()}
                        </span>
                    </div>
                    {deploymentDetails.failure_reason && (
                        <div className="deployment-detail-item">
                            <span className="deployment-detail-label">FAILURE REASON</span>
                            <span className="deployment-detail-value deployment-detail-failure">
                                {deploymentDetails.failure_reason}
                            </span>
                        </div>
                    )}
                </section>

                <section className="deployment-details-section">
                    <h2>Timeline</h2>
                    <DeploymentTimeline status={deploymentDetails.status} />
                </section>

                <section className="deployment-details-section">
                    <BuildLogs logs={[]} />
                </section>
            </main>
        </div>
    )
}

export default DeploymentDetails
