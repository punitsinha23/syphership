import { Link } from "react-router-dom"
import logo from "../../assets/logo.png"
import "./Logo.css"

// Width / height of the SYPHER//SHIP lockup artwork
const LOGO_RATIO = 1685 / 283

// The "S" mark with the SYPHER//SHIP wordmark. `size` is the logo's height in px.
export function Logo({ to = "/", size = 28, className = "" }) {
    return (
        <Link className={`logo ${className}`} to={to} aria-label="Syphership home">
            <img
                className="logo-image"
                src={logo}
                width={Math.round(size * LOGO_RATIO)}
                height={size}
                alt="Syphership"
            />
        </Link>
    )
}
