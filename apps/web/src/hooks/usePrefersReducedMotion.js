import { useEffect, useState } from 'react'

/**
 * usePrefersReducedMotion — the operating system's motion preference.
 *
 * Apple HIG §14: when the system asks for reduced motion, transitions
 * become cross-fades or disappear entirely. The product honours that in
 * CSS as well as here, so the two never disagree.
 */
export function usePrefersReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  })

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return undefined

    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = (event) => setPrefersReducedMotion(event.matches)

    // Safari below 14 only supports the deprecated listener API.
    if (query.addEventListener) {
      query.addEventListener('change', onChange)
      return () => query.removeEventListener('change', onChange)
    }

    query.addListener(onChange)
    return () => query.removeListener(onChange)
  }, [])

  return prefersReducedMotion
}
