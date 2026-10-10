import { apiFetch } from "./client"


export function getRepos(page = 1) {
    return apiFetch(`/github/repos?page=${page}`)
}

export function getBranches(fullName) {
    return apiFetch(`/github/repos/${fullName}/branches`)
}
