import { useEffect, useRef } from "react"
import "./RocketCursor.css"

export function RocketCursor() {
    const cursorRef = useRef(null)
    const trailRef = useRef(null)

    useEffect(() => {
        const cursor = cursorRef.current
        const trail = trailRef.current
        let mouseX = 0
        let mouseY = 0
        let cursorX = 0
        let cursorY = 0
        let trailX = 0
        let trailY = 0
        let animationId

        function onMouseMove(e) {
            mouseX = e.clientX
            mouseY = e.clientY
        }

        function animate() {
            cursorX += (mouseX - cursorX) * 0.2
            cursorY += (mouseY - cursorY) * 0.2
            trailX += (mouseX - trailX) * 0.1
            trailY += (mouseY - trailY) * 0.1

            if (cursor) {
                cursor.style.transform = `translate(${cursorX}px, ${cursorY}px)`
            }
            if (trail) {
                trail.style.transform = `translate(${trailX}px, ${trailY}px)`
            }

            animationId = requestAnimationFrame(animate)
        }

        window.addEventListener("mousemove", onMouseMove)
        animationId = requestAnimationFrame(animate)

        return () => {
            window.removeEventListener("mousemove", onMouseMove)
            cancelAnimationFrame(animationId)
        }
    }, [])

    return (
        <>
            <div ref={trailRef} className="rocket-trail" />
            <div ref={cursorRef} className="rocket-cursor">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path
                        d="M12 2L15 8L12 22L9 8L12 2Z"
                        fill="#22D3EE"
                        opacity="0.9"
                    />
                    <path
                        d="M9 8L12 2L15 8L12 14L9 8Z"
                        fill="#67E8F9"
                    />
                    <circle cx="12" cy="8" r="1.5" fill="#F5F7FA" />
                </svg>
            </div>
        </>
    )
}
