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

export function updateStatus(deployment_id, status) {
    return apiFetch(`/deployments/${deployment_id}/status`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            status: status
        })
    })
}

export function getDeployment(deployment_id){
    return apiFetch(`/deployments/${deployment_id}`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json"
        }
    })
}
