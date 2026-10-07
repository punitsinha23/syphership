import { useState } from "react"
import { useNavigate, Link } from "react-router-dom"
import "./Register.css"


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

        if(!response.ok){
            setError(data.detail)
            return
        }

        navigate("/login")

    }
    return(
        <div className="register-page">
            <div className="register-container">
                <div className="register-header">
                    <p className="register-logo">
                        <span>SYPHER</span>
                        <span className="register-logo-accent">//</span>
                        <span>SHIP</span>
                    </p>
                    <h1 className="register-title">Create your account</h1>
                    <p className="register-subtitle">Start shipping your code into orbit</p>
                </div>

                <form className="register-form" onSubmit={handleSubmit}>
                    <div className="register-field">
                        <label htmlFor="register-email">Email</label>
                        <input
                            id="register-email"
                            type="email"
                            value={email}
                            onChange={(event) => {
                                setEmail(event.target.value)
                                setError("")
                            }}
                            placeholder="you@example.com"
                        />
                    </div>

                    <div className="register-field">
                        <label htmlFor="register-username">Username</label>
                        <input
                            id="register-username"
                            type="text"
                            value={username}
                            onChange={(event) => {
                                setUsername(event.target.value)
                                setError("")
                            }}
                            placeholder="Choose a username"
                        />
                    </div>

                    <div className="register-field">
                        <label htmlFor="register-password">Password</label>
                        <input
                            id="register-password"
                            type="password"
                            value={password}
                            onChange={(event) => {
                                setPassword(event.target.value)
                                setError("")
                            }}
                            placeholder="At least 8 characters"
                        />
                    </div>

                    <button className="register-button" type="submit">
                        Create Account
                    </button>

                    {error && <p className="register-error">{error}</p>}
                </form>

                <p className="register-footer">
                    Already have an account? <Link to="/login">Sign in</Link>
                </p>
            </div>
        </div>
    )
}

export default Register
