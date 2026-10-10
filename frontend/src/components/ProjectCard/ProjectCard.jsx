import "./ProjectCard.css"
import { Link } from "react-router-dom"
import { StatusBadge } from "../StatusBadge/StatusBadge"
import { shortSha, timeAgo } from "../../utils/time"


export function ProjectCard({ project, latestDeployment }) {
    return (
        <Link className="project-card" to={`/projects/${project.id}`}>
            <div className="project-card-top">
                <span className="project-card-icon" aria-hidden="true">
                    {project.name.charAt(0).toUpperCase()}
                </span>
                <StatusBadge status={latestDeployment?.status} />
            </div>

            <h2>{project.name}</h2>
            {project.repo_full_name && (
                <span className="project-card-repo">
                    {project.repo_full_name}
                    <span className="project-card-branch">{project.repo_branch}</span>
                </span>
            )}
            <p>{project.description || "No description"}</p>

            <div className="project-card-footer">
                {latestDeployment ? (
                    <>
                        <code>{shortSha(latestDeployment.commit_sha)}</code>
                        <span>{timeAgo(latestDeployment.created_at)}</span>
                    </>
                ) : (
                    <span>Created {timeAgo(project.created_at)}</span>
                )}
            </div>
        </Link>
    )
}
