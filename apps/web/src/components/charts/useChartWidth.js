import { useEffect, useRef, useState } from 'react'

/**
 * useChartWidth — the rendered width of a chart container.
 *
 * SVG needs a pixel coordinate system to place labels and hit targets
 * correctly; scaling a fixed viewBox instead would scale the type with it.
 * A ResizeObserver keeps the chart honest when the layout reflows.
 */
export function useChartWidth(fallback = 640) {
  const ref = useRef(null)
  const [width, setWidth] = useState(fallback)

  useEffect(() => {
    const node = ref.current
    if (!node) return undefined

    const measure = () => setWidth(Math.max(280, node.clientWidth))
    measure()

    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', measure)
      return () => window.removeEventListener('resize', measure)
    }

    const observer = new ResizeObserver(measure)
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  return [ref, width]
}
