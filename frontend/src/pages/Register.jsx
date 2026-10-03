import { useState } from "react"
import { useNavigate } from "react-router-dom"


function Register(){
    const[email, setEmail] = useState("")
    const[username, setUsername] = useState("")
    const[password, setPassword] = useState("")
    const[error, setError] = useState("")
    const navigate = useNavigate()

    
async function handleSubmit(event){
    event.preventDefault()
     
    if(email == ""){
        setError("Email can't be empty")
        return
    }

    if(username == ""){
        setError("username can't be empty")
        return
    }

    if(password == ""){
        setError("password cant be empty")
        return
    }

    const response = await fetch("http://localhost:8000/auth/register", {
        method: "Post",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            email: email,
            username: username,
            password: password
        })

    })

    const data = await response.json()

    console.log(response.status)
    console.log(data)

    if(!response.ok){
        setError(data.detail)
        return
    }

    navigate("/login")

}
    return(
        <div>
            <h1>create account</h1>
            <form onSubmit={handleSubmit}>
            <label>Email: </label>
            <input 
                type="email"
                value={email}
                onChange={(event) => {
                    setEmail(event.target.value)
                    setError("")
                }}
            />
            <label>Username: </label>
            <input 
                type="text"
                value={username}
                onChange={(event) => {
                    setUsername(event.target.value)
                    setError("")
                }}
            />
            <label>Password: </label>
            <input 
                type="password"
                value={password}
                onChange={(event) => {
                    setPassword(event.target.value)
                    setError("")
                }}
            />
            <button type="submit">Submit</button>
            </form>
            {error && <p>{error}</p>}
        </div>
    )
}

export default Register