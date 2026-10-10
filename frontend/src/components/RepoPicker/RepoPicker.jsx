import { useEffect, useState } from "react"
import { getRepos } from "../../api/github"
import { connectGitHub } from "../../api/auth"
import "./RepoPicker.css"

const PAGE_SIZE = 100 
export function RepoPicker({ selected, onSelect }) {
    const [repos, setRepos] = useState([])
    const [page, setPage] = useState(1)
    const [hasMore, setHasMore] = useState(false)
    const [loading, setLoading] = useState(true)
    const [loadingMore, setLoadingMore] = useState(false)
    const [error, setError] = useState(null)
    const [query, setQuery] = useState("")
    const [connecting, setConnecting] = useState(false)

    function showPage(pageToLoad, data) {
        setRepos((current) => (pageToLoad === 1 ? data : [...current, ...data]))
        setPage(pageToLoad)
        setHasMore(data.length === PAGE_SIZE)
        setError(null)
    }

    function showError(err) {
        setError({ message: err.message, status: err.status })
    }

    function loadPage(pageToLoad) {
        return getRepos(pageToLoad)
            .then((data) => showPage(pageToLoad, data))
            .catch(showError)
    }

    useEffect(() => {
        getRepos(1)
            .then((data) => showPage(1, data))
            .catch(showError)
            .finally(() => setLoading(false))
    }, [])

    async function handleRetry() {
        setLoading(true)
        await loadPage(1)
        setLoading(false)
    }

    async function handleLoadMore() {
        setLoadingMore(true)
        await loadPage(page + 1)
        setLoadingMore(false)
    }

    async function handleConnect() {
        try {
            setConnecting(true)
            await connectGitHub()
        } catch (err) {
            setError({ message: err.message })
            setConnecting(false)
        }
    }

    const search = query.trim().toLowerCase()
    const visibleRepos = search
        ? repos.filter((repo) => repo.full_name.toLowerCase().includes(search))
        : repos

    return (
        <div className="repo-picker">
            <div className="repo-picker-header">
                <span className="field-label">
                    Git repository <span className="field-optional">optional</span>
                </span>
                {selected && (
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => onSelect(null)}>
                        Create without a repository
                    </button>
                )}
            </div>

            {loading ? (
                <div className="repo-picker-state">Loading repositories…</div>
            ) : error?.status === 403 ? (
                // Not connected, or access was revoked on GitHub: reconnecting fixes both
                <div className="alert alert-info repo-picker-alert">
                    <span>{error.message}</span>
                    <button type="button" className="btn btn-secondary btn-sm" onClick={handleConnect} disabled={connecting}>
                        {connecting ? "Redirecting…" : "Connect GitHub"}
                    </button>
                </div>
            ) : error ? (
                <div className="alert alert-error repo-picker-alert">
                    <span>{error.message}</span>
                    <button type="button" className="btn btn-secondary btn-sm" onClick={handleRetry}>
                        Retry
                    </button>
                </div>
            ) : (
                <>
                    <input
                        className="input repo-picker-search"
                        type="search"
                        value={query}
                        onChange={(event) => setQuery(event.target.value)}
                        placeholder={`Search ${repos.length} repositories…`}
                        aria-label="Search repositories"
                    />

                    {visibleRepos.length === 0 ? (
                        <div className="repo-picker-state">
                            {search ? `No repositories match “${query.trim()}”.` : "No repositories found on your GitHub account."}
                        </div>
                    ) : (
                        <ul className="repo-list">
                            {visibleRepos.map((repo) => {
                                const isSelected = selected?.id === repo.id

                                return (
                                    <li key={repo.id}>
                                        <button
                                            type="button"
                                            className={`repo-row ${isSelected ? "repo-row-selected" : ""}`}
                                            onClick={() => onSelect(isSelected ? null : repo)}
                                            aria-pressed={isSelected}
                                        >
                                            <svg className="repo-row-icon" width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                                                <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z" />
                                            </svg>
                                            <span className="repo-row-name">{repo.full_name}</span>
                                            {repo.private && <span className="repo-row-badge">Private</span>}
                                            <span className="repo-row-action">{isSelected ? "Selected ✓" : "Select"}</span>
                                        </button>
                                    </li>
                                )
                            })}
                        </ul>
                    )}

                    {hasMore && !search && (
                        <button type="button" className="btn btn-ghost btn-sm repo-picker-more" onClick={handleLoadMore} disabled={loadingMore}>
                            {loadingMore ? "Loading…" : "Load more repositories"}
                        </button>
                    )}
                </>
            )}
        </div>
    )
}
