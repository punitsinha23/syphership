import { Link } from "react-router-dom"
import { OAuthButtons } from "../../components/OAuthButtons/OAuthButtons"
import "./Login.css"


function Login(){
    return(
        <div className="login-page">
            <div className="login-container">
                <div className="login-header">
                    <Link className="login-logo" to="/">
                        <span>SYPHER</span>
                        <span className="login-logo-accent">//</span>
                        <span>SHIP</span>
                    </Link>
                    <h1 className="login-title">Welcome back</h1>
                    <p className="login-subtitle">Sign in to your account to continue</p>
                </div>

                <div className="login-card">
                    <OAuthButtons />
                </div>
            </div>
        </div>
    )
}

export default Login
