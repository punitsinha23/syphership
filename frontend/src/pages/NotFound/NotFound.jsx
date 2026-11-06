import { Link } from "react-router-dom"
import { PublicLayout } from "../../components/PublicLayout/PublicLayout"
import "./NotFound.css"

function NotFound() {
    const signedIn = Boolean(localStorage.getItem("access_token"))

    return (
        <PublicLayout>
            <main className="not-found">
                <p className="eyebrow">404</p>
                <h1 className="not-found-title">Page not found</h1>
                <p className="not-found-text">
                    This page doesn't exist, or it has moved.
                </p>
                <Link className="btn btn-primary" to={signedIn ? "/dashboard" : "/"}>
                    {signedIn ? "Back to dashboard" : "Back to home"}
                </Link>
            </main>
        </PublicLayout>
    )
}

export default NotFound
