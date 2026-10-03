import { useState, useEffect} from "react";
import { getProjects, createProject } from "../api/projects";
import { ProjectCard } from "../components/ProjectCard";


function Projects(){
    const [name, setName] = useState("")
    const [description, setDescription] = useState("")
    const [projects, setProjects] = useState([])
    const [loading , setLoading] = useState(true)
    const [error , setError] = useState("")

    useEffect(() => {
        async function loadProjects() {
            try{
                const data = await getProjects()
                setProjects(data)
            }catch(error){
                setError(error.message)
            }finally{
                setLoading(false)
            }
        }
    loadProjects()
    }, [])
    
    async function handleSubmit(event){
        event.preventDefault()

        try{
            const data = await createProject(name, description)
            setProjects((currentProjects) => [...currentProjects, data])
        }catch(error){
            setError(error.message)
        }
    }


    return (
        <div>
            <div>
            <h1>Create project</h1>
            <form onSubmit={handleSubmit}>
                <label>Name: </label>
                <input 
                    type="text"
                    value={name}
                    onChange={(event)=> setName(event.target.value)}
                />
                <label>Description</label>
                <input 
                    type="text"
                    value={description}
                    onChange={(event)=> setDescription(event.target.value)}
                />
                <button type="submit">Create</button>
            </form>
            </div>
            <div>
                <h1>Projects</h1>
                {loading && <p>Loading...</p>}
                {error && <p>{error}</p>}
                {!loading && !error && projects.length === 0 &&(
                    <p>No projects yet</p>
                )}

                {projects.map((project) => (
                    <div>
                        <ProjectCard key={project.id} project={project}/>
                    </div>
                ))}
            </div>
        </div>
    )

}

export default Projects
