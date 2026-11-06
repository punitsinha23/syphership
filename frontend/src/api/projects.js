import { apiFetch } from "./client"

export function getProjects() {
    return apiFetch("/projects/")
}

export function getProjectDetails(project_id) {
    return apiFetch(`/projects/${project_id}`)
}


export function createProject(name, description, repoFullName = null, repoBranch = null) {
    return apiFetch("/projects/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            name: name,
            description: description,
            repo_full_name: repoFullName,
            repo_branch: repoBranch
        })
    })
}

export function updateProject(project, changes) {
    return apiFetch(`/projects/${project.id}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            name: project.name,
            description: project.description,
            ...changes
        })
    })
}

export function enableWebhook(project_id) {
    return apiFetch(`/projects/${project_id}/webhook`, { method: "POST" })
}

export function getEnvVars(project_id) {
    return apiFetch(`/projects/${project_id}/env`)
}

// A null value deletes that variable
export function updateEnvVars(project_id, variables) {
    return apiFetch(`/projects/${project_id}/env`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ variables })
    })
}

// The API deploys the latest commit of the project's branch
export function createDeployment(project_id) {
    return apiFetch("/deployments/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            project_id: project_id
        })
    })
}


export function getAllDeployments() {
    return apiFetch("/deployments/")
}


export function latestByProject(deployments) {
    const latest = {}
    for (const deployment of deployments) {
        latest[deployment.project_id] ??= deployment
    }
    return latest
}

export function getDeployments(project_id) {
    return apiFetch(`/deployments/?project_id=${project_id}`)
}

export function deleteProject(project_id) {
    return apiFetch(`/projects/${project_id}`, { method: "DELETE" })
}

export function deleteDeployment(deployment_id) {
    return apiFetch(`/deployments/${deployment_id}`, { method: "DELETE" })
}

export function getDeploymentLogs(deployment_id) {
    return apiFetch(`/deployments/${deployment_id}/logs`)
}

export function getDeployment(deployment_id){
    return apiFetch(`/deployments/${deployment_id}`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json"
        }
    })
}
