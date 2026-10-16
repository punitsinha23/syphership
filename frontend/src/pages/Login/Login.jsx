import { OAuthButtons } from "../../components/OAuthButtons/OAuthButtons"
import { Logo } from "../../components/Logo/Logo"
import "./Login.css"


function Login(){
    return(
        <div className="login-page">
            <div className="login-container">
                <div className="login-header">
                    <Logo className="login-logo" size={40} />
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
