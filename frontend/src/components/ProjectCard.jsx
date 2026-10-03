import "./ProjectCard.css"
import { useNavigate } from "react-router-dom"



export function ProjectCard({project}){
    const navigate = useNavigate()

    return(
    <div className="project-card"
    onClick={() => navigate(`/projects/${project.id}`)}
    >
    <h2>{project.name}</h2>
    <p>{project.description}</p>
    </div>
)}


