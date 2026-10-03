import { useState } from "react"
import { useNavigate } from "react-router-dom"


function Login(){
    const[email, setEmail] = useState("")
    const[password, setPassword] = useState("")
    const[error, setError] = useState("")
    const navigate = useNavigate()

    
async function handleSubmit(event){
    event.preventDefault()
     
    if(email == ""){
        setError("Email can't be empty")
        return
    }

    if(password == ""){
        setError("password cant be empty")
        return
    }

    const response = await fetch("http://localhost:8000/auth/login", {
        method: "Post",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            email: email,
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

    navigate("/dashboard")
    localStorage.setItem("access_token", data.access_token)
    localStorage.setItem("refresh_token", data.refresh_token)
    


}
    return(
        <div>
            <h1>Login</h1>
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

export default Login