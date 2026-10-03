import { apiFetch } from "./client"

export function getProjects() {
    return apiFetch("/projects")
}

export function getProjectDetails(project_id) {
    return apiFetch(`/projects/${project_id}`)
}

export function createProject(name, description) {
    return apiFetch("/projects/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            name: name,
            description: description
        })
    })
}

export function createDeployment(project_id, commit_sha) {
    return apiFetch("/deployments/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            project_id: project_id,
            commit_sha: commit_sha
        })
    })
}

export async function getDeployments(){
    const token = localStorage.getItem("access_token")

    const response = await fetch("http://localhost:8000/deployments/",{
        method: "GET",
        headers: {
            "Authorization": `Bearer ${token}`
        },
    })

    if(!response.ok){
        const error = await response.json()
        throw new Error(error.message || "Failed to fetch deployment");
    }

    const data = await response.json()

    return data
}

export async function updateStatus(deployment_id, status) {
    const token = localStorage.getItem("access_token")

    return apiFetch(`/deployments/${deployment_id}/status`,{
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
            "status": status
        })
    })

}