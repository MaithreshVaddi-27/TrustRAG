import { useEffect } from 'react'

/**
 * usePointerParallax — a few pixels of depth, driven by the pointer.
 *
 * It writes two normalised CSS variables (−1 … 1) on the target; the
 * stylesheet decides how far that moves a decorative layer. The work is
 * throttled to one update per frame, input is never locked, and the values
 * reset the moment the pointer leaves. Coarse pointers and reduced-motion
 * users get no listeners at all.
 */
export default function usePointerParallax(ref) {
  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    if (typeof window === 'undefined') return undefined
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined
    if (window.matchMedia?.('(pointer: coarse)').matches) return undefined

    let frame = 0

    const onMove = (event) => {
      if (frame) return
      frame = requestAnimationFrame(() => {
        frame = 0
        const rect = el.getBoundingClientRect()
        if (!rect.width || !rect.height) return
        const x = ((event.clientX - rect.left) / rect.width - 0.5) * 2
        const y = ((event.clientY - rect.top) / rect.height - 0.5) * 2
        el.style.setProperty('--field-x', Math.max(-1, Math.min(1, x)).toFixed(3))
        el.style.setProperty('--field-y', Math.max(-1, Math.min(1, y)).toFixed(3))
      })
    }

    const onLeave = () => {
      el.style.setProperty('--field-x', '0')
      el.style.setProperty('--field-y', '0')
    }

    el.addEventListener('pointermove', onMove, { passive: true })
    el.addEventListener('pointerleave', onLeave)
    return () => {
      if (frame) cancelAnimationFrame(frame)
      el.removeEventListener('pointermove', onMove)
      el.removeEventListener('pointerleave', onLeave)
      onLeave()
    }
  }, [ref])
}
