import { apiFetch, authorizedFetch } from "./client"

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

// Follow a build's output live (Server-Sent Events). Calls onLine(text) for each
// line, from the start of the build, and resolves when the build output ends.
// fetch instead of EventSource, because EventSource can't send the
// Authorization header. Stop it early with an AbortController's signal.
export async function streamDeploymentLogs(deployment_id, { onLine, signal }) {
    const response = await authorizedFetch(`/deployments/${deployment_id}/logs/stream`, { signal })
    if (!response.ok || !response.body) {
        throw new Error(`Live logs unavailable (${response.status})`)
    }

    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
    let buffer = ""

    while (true) {
        const { value, done } = await reader.read()
        if (done) return
        buffer += value

        // Events are separated by a blank line; the last piece may be incomplete.
        const events = buffer.split("\n\n")
        buffer = events.pop()

        for (const event of events) {
            let type = "message"
            let data = null
            for (const line of event.split("\n")) {
                if (line.startsWith("event: ")) type = line.slice(7)
                else if (line.startsWith("data: ")) data = line.slice(6)
            }
            if (type === "end") return
            if (type === "message" && data) onLine(JSON.parse(data))
        }
    }
}

export function getDeployment(deployment_id){
    return apiFetch(`/deployments/${deployment_id}`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json"
        }
    })
}
