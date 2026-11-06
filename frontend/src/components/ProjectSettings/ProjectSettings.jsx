import { useEffect, useState } from "react"
import { enableWebhook, getEnvVars, updateEnvVars, updateProject } from "../../api/projects"
import "./ProjectSettings.css"

export function ProjectSettings({ project, onProjectChange }) {
    const [names, setNames] = useState([])
    const [newName, setNewName] = useState("")
    const [newValue, setNewValue] = useState("")
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        let cancelled = false

        getEnvVars(project.id)
            .then((data) => {
                if (!cancelled) setNames(data.names)
            })
            .catch((error) => {
                if (!cancelled) setError(error.message)
            })

        return () => {
            cancelled = true
        }
    }, [project.id])

    // Runs one save at a time and shows its error in this section
    async function run(action) {
        try {
            setSaving(true)
            setError(null)
            await action()
        } catch (error) {
            setError(error.message)
        } finally {
            setSaving(false)
        }
    }

    function handleToggleAutoDeploy(event) {
        const autoDeploy = event.target.checked
        return run(async () => {
            onProjectChange(await updateProject(project, { auto_deploy: autoDeploy }))
        })
    }

    function handleEnableWebhook() {
        return run(async () => {
            onProjectChange(await enableWebhook(project.id))
        })
    }

    function handleAddVariable(event) {
        event.preventDefault()
        return run(async () => {
            const data = await updateEnvVars(project.id, { [newName]: newValue })
            setNames(data.names)
            setNewName("")
            setNewValue("")
        })
    }

    function handleDeleteVariable(name) {
        return run(async () => {
            const data = await updateEnvVars(project.id, { [name]: null })
            setNames(data.names)
        })
    }

    return (
        <section className="section">
            <div className="section-header">
                <h2 className="section-title">Settings</h2>
            </div>

            {error && <div className="alert alert-error">{error}</div>}

            <div className="card project-settings">
                {project.repo_full_name && (
                    <div className="project-settings-row">
                        <div>
                            <h3 className="project-settings-title">Deploy on push</h3>
                            <p className="project-settings-help">
                                {project.webhook_active
                                    ? `Pushes to ${project.repo_branch} deploy automatically.`
                                    : "No webhook on this repository yet. You need admin access to add one."}
                            </p>
                        </div>
                        {project.webhook_active ? (
                            <label className="project-settings-toggle">
                                <input
                                    type="checkbox"
                                    checked={project.auto_deploy}
                                    onChange={handleToggleAutoDeploy}
                                    disabled={saving}
                                />
                                <span>{project.auto_deploy ? "On" : "Off"}</span>
                            </label>
                        ) : (
                            <button className="btn btn-secondary btn-sm" onClick={handleEnableWebhook} disabled={saving}>
                                Enable
                            </button>
                        )}
                    </div>
                )}

                <div className="project-settings-block">
                    <h3 className="project-settings-title">Environment variables</h3>
                    <p className="project-settings-help">
                        Values are encrypted and can't be viewed after saving. Changes apply on the next deployment.
                    </p>

                    {names.length > 0 && (
                        <ul className="project-settings-vars">
                            {names.map((name) => (
                                <li key={name} className="project-settings-var">
                                    <code>{name}</code>
                                    <span className="project-settings-mask">••••••••</span>
                                    <button
                                        className="btn btn-danger btn-sm"
                                        onClick={() => handleDeleteVariable(name)}
                                        disabled={saving}
                                    >
                                        Delete
                                    </button>
                                </li>
                            ))}
                        </ul>
                    )}

                    <form className="project-settings-form" onSubmit={handleAddVariable}>
                        <input
                            className="input"
                            placeholder="NAME"
                            aria-label="Variable name"
                            value={newName}
                            onChange={(event) => setNewName(event.target.value)}
                            autoComplete="off"
                            required
                        />
                        <input
                            className="input"
                            type="password"
                            placeholder="Value"
                            aria-label="Variable value"
                            value={newValue}
                            onChange={(event) => setNewValue(event.target.value)}
                            autoComplete="new-password"
                            required
                        />
                        <button className="btn btn-secondary" type="submit" disabled={saving}>
                            Save
                        </button>
                    </form>
                </div>
            </div>
        </section>
    )
}
