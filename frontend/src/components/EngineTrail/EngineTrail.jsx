import { useEffect, useRef } from "react"
import "./EngineTrail.css"

// The cursor is public/cursors/ship.svg with its hotspot on the nose (6, 6);
// the engine nozzle sits 15.7px right and down from there.
const TAIL_OFFSET = 15.7
// How long a point of the beam stays visible, in ms
const TRAIL_LIFE = 260
// Longest the beam may get on fast moves, in px
const MAX_LENGTH = 90

// Draws a short fading engine beam behind the spaceship cursor
export function EngineTrail() {
    const canvasRef = useRef(null)

    useEffect(() => {
        const finePointer = window.matchMedia("(any-pointer: fine)").matches
        const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches
        if (!finePointer || reduceMotion) return

        const canvas = canvasRef.current
        const ctx = canvas.getContext("2d")
        let points = []
        let frame = null

        function resize() {
            const dpr = window.devicePixelRatio || 1
            canvas.width = window.innerWidth * dpr
            canvas.height = window.innerHeight * dpr
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
        }

        function draw() {
            const now = performance.now()
            points = points.filter((point) => now - point.t < TRAIL_LIFE)

            // Keep the beam short: drop the oldest points beyond MAX_LENGTH
            let length = 0
            for (let i = points.length - 1; i > 0; i--) {
                length += Math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y)
                if (length > MAX_LENGTH) {
                    points = points.slice(i - 1)
                    break
                }
            }

            ctx.clearRect(0, 0, window.innerWidth, window.innerHeight)
            ctx.lineCap = "round"

            for (let i = 1; i < points.length; i++) {
                const from = points[i - 1]
                const to = points[i]
                // Fade with age and toward the old end, so a capped beam still tapers out
                const life = (1 - (now - to.t) / TRAIL_LIFE) * (i / (points.length - 1))

                // soft outer glow
                ctx.strokeStyle = `rgba(34, 211, 238, ${life * 0.25})`
                ctx.lineWidth = 2 + life * 5
                ctx.beginPath()
                ctx.moveTo(from.x, from.y)
                ctx.lineTo(to.x, to.y)
                ctx.stroke()

                // bright core
                ctx.strokeStyle = `rgba(165, 243, 252, ${life * 0.9})`
                ctx.lineWidth = 0.5 + life * 2
                ctx.stroke()
            }

            // Keep animating only while there is something left to fade
            frame = points.length > 0 ? requestAnimationFrame(draw) : null
        }

        function onPointerMove(event) {
            // Text fields show an I-beam instead of the ship, so no exhaust there
            if (event.target.closest?.("input, textarea")) return

            points.push({
                x: event.clientX + TAIL_OFFSET,
                y: event.clientY + TAIL_OFFSET,
                t: performance.now(),
            })

            if (frame === null) frame = requestAnimationFrame(draw)
        }

        function onLeave() {
            points = []
        }

        resize()
        window.addEventListener("resize", resize)
        window.addEventListener("pointermove", onPointerMove, { passive: true })
        document.documentElement.addEventListener("mouseleave", onLeave)

        return () => {
            window.removeEventListener("resize", resize)
            window.removeEventListener("pointermove", onPointerMove)
            document.documentElement.removeEventListener("mouseleave", onLeave)
            if (frame !== null) cancelAnimationFrame(frame)
        }
    }, [])

    return <canvas ref={canvasRef} className="engine-trail" aria-hidden="true" />
}
