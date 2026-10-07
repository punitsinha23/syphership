import { useState } from "react"
import { useNavigate, Link } from "react-router-dom"
import "./Login.css"


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

        if(!response.ok){
            setError(data.detail)
            return
        }

        localStorage.setItem("access_token", data.access_token)
        localStorage.setItem("refresh_token", data.refresh_token)
        navigate("/dashboard")


    }
    return(
        <div className="login-page">
            <div className="login-container">
                <div className="login-header">
                    <p className="login-logo">
                        <span>SYPHER</span>
                        <span className="login-logo-accent">//</span>
                        <span>SHIP</span>
                    </p>
                    <h1 className="login-title">Welcome back</h1>
                    <p className="login-subtitle">Sign in to your account to continue</p>
                </div>

                <form className="login-form" onSubmit={handleSubmit}>
                    <div className="login-field">
                        <label htmlFor="login-email">Email</label>
                        <input
                            id="login-email"
                            type="email"
                            value={email}
                            onChange={(event) => {
                                setEmail(event.target.value)
                                setError("")
                            }}
                            placeholder="you@example.com"
                        />
                    </div>

                    <div className="login-field">
                        <label htmlFor="login-password">Password</label>
                        <input
                            id="login-password"
                            type="password"
                            value={password}
                            onChange={(event) => {
                                setPassword(event.target.value)
                                setError("")
                            }}
                            placeholder="Enter your password"
                        />
                    </div>

                    <button className="login-button" type="submit">
                        Sign In
                    </button>

                    {error && <p className="login-error">{error}</p>}
                </form>

                <p className="login-footer">
                    Don't have an account? <Link to="/register">Create one</Link>
                </p>
            </div>
        </div>
    )
}

export default Login
