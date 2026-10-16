import { useEffect, useRef } from "react"

// Props for an element that fades up when it scrolls into view.
// `delay` (ms) staggers items that enter together.
export function reveal(delay = 0) {
    return {
        "data-reveal": "",
        style: { "--reveal-delay": `${delay}ms` },
    }
}

// Attach the returned ref to a container; every [data-reveal] inside it is
// shown once, the first time it scrolls into view.
export function useScrollReveal() {
    const containerRef = useRef(null)

    useEffect(() => {
        const container = containerRef.current
        const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
        if (!container || reduceMotion || !("IntersectionObserver" in window)) return

        const observer = new IntersectionObserver(
            (entries) => {
                for (const entry of entries) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible")
                        observer.unobserve(entry.target)
                    }
                }
            },
            // Trigger a little before the element is fully on screen
            { rootMargin: "0px 0px -8% 0px", threshold: 0.1 }
        )

        container.querySelectorAll("[data-reveal]").forEach((element) => observer.observe(element))

        // Content stays visible without JS; it is only hidden once observing starts
        container.classList.add("reveal-ready")

        return () => observer.disconnect()
    }, [])

    return containerRef
}
