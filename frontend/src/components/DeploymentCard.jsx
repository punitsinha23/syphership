import "./DeploymentCard.css"
import { useState } from "react"
import { updateStatus } from "../api/projects"


export function DeploymentCard({deployment}){
    const [status, setStatus] = useState(deployment.status)
    
    async function handleSubmit() {
        const nextStatus = {
             QUEUED: "BUILDING",
            BUILDING: "DEPLOYING",
            DEPLOYING: "RUNNING"
        }[status]

        if(!nextStatus) return
        
        try{
        const data = await updateStatus(deployment.id, nextStatus)
            setStatus(data.status)
        
        }catch(error){
            console.error(error.message)
        }
    }
    return(
    <div className="deployment-card">
        <h2>Status: {status}</h2>
        <p>{deployment.commit_sha}</p>
        <small>created at: {new Date(deployment.created_at).toLocaleString()}</small>
        <button
        onClick={handleSubmit}
        disabled={status === "RUNNING"}
        >{status === "RUNNING" ? "Deployment complete" : "Change status"}</button>
    </div>
    )
}

