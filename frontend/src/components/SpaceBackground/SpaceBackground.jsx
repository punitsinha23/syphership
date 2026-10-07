import { useEffect, useRef } from "react"
import "./SpaceBackground.css"

export function SpaceBackground() {
    const canvasRef = useRef(null)

    useEffect(() => {
        const canvas = canvasRef.current
        const ctx = canvas.getContext("2d")
        let animationId
        let stars = []

        function resize() {
            canvas.width = window.innerWidth
            canvas.height = window.innerHeight
            initStars()
        }

        function initStars() {
            stars = []
            const count = Math.floor((canvas.width * canvas.height) / 8000)
            for (let i = 0; i < count; i++) {
                stars.push({
                    x: Math.random() * canvas.width,
                    y: Math.random() * canvas.height,
                    size: Math.random() * 1.5 + 0.5,
                    opacity: Math.random() * 0.5 + 0.2,
                    twinkleSpeed: Math.random() * 0.02 + 0.005,
                    twinkleOffset: Math.random() * Math.PI * 2
                })
            }
        }

        function drawStars(time) {
            ctx.clearRect(0, 0, canvas.width, canvas.height)

            stars.forEach(star => {
                const twinkle = Math.sin(time * star.twinkleSpeed + star.twinkleOffset) * 0.3 + 0.7
                ctx.beginPath()
                ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2)
                ctx.fillStyle = `rgba(255, 255, 255, ${star.opacity * twinkle})`
                ctx.fill()
            })

            animationId = requestAnimationFrame(drawStars)
        }

        resize()
        window.addEventListener("resize", resize)
        animationId = requestAnimationFrame(drawStars)

        return () => {
            window.removeEventListener("resize", resize)
            cancelAnimationFrame(animationId)
        }
    }, [])

    return (
        <div className="space-background">
            <canvas ref={canvasRef} className="space-stars" />
            <div className="space-orbit space-orbit-1" />
            <div className="space-orbit space-orbit-2" />
            <div className="space-orbit space-orbit-3" />
        </div>
    )
}
