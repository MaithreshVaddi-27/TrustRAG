import { useEffect } from 'react'
import { useMotionValue, useSpring } from 'motion/react'

/**
 * useCursorGlow - Tracks mouse position for cursor glow effect
 * Called by: AppLayout.jsx (lines 47-77)
 * No existing file serves this purpose - extracted from AppLayout
 * Reads/writes: motion values for cursor position
 * User instruction: "continue and Use asynchronous methods for better working with async and await"
 */
export function useCursorGlow(reducedMotion) {
  const cursorX = useMotionValue(0)
  const cursorY = useMotionValue(0)
  const glowX = useSpring(cursorX, { damping: 30, stiffness: 200 })
  const glowY = useSpring(cursorY, { damping: 30, stiffness: 200 })

  useEffect(() => {
    if (reducedMotion) return undefined
    if (typeof window !== 'undefined' && window.matchMedia?.('(pointer: coarse)').matches) return undefined

    let raf = 0
    let pending = null

    const flush = () => {
      raf = 0
      if (pending) {
        cursorX.set(pending.x)
        cursorY.set(pending.y)
        pending = null
      }
    }

    const handler = (e) => {
      pending = { x: e.clientX, y: e.clientY }
      if (!raf) raf = requestAnimationFrame(flush)
    }

    window.addEventListener('mousemove', handler, { passive: true })
    return () => {
      window.removeEventListener('mousemove', handler)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [cursorX, cursorY, reducedMotion])

  return { glowX, glowY }
}