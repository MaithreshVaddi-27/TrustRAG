import { useEffect } from 'react'

/**
 * useScrollReveal — one authored entrance.
 *
 * Elements marked `data-lx-reveal` rise 16px as they enter the viewport,
 * once. Nothing loops.
 *
 * Only elements that are BELOW the fold at mount are ever hidden. Anything
 * already in view is left visible immediately, so content can never be
 * stranded by a failed observer, a print, or an unusual layout. The `lx-js`
 * class on <html> is the second guard: without JavaScript the hidden state
 * does not exist at all.
 *
 * @param {string} selector  CSS selector for the elements to reveal.
 * @param {object} options
 * @param {number} options.threshold  Fraction of the element that must be
 *                                     visible before it reveals.
 * @param {string} options.rootMargin  IntersectionObserver root margin.
 * @returns {void}
 */
export default function useScrollReveal(selector = '[data-lx-reveal]', options = {}) {
  const { threshold = 0.12, rootMargin = '0px 0px -6% 0px' } = options

  useEffect(() => {
    const root = document.documentElement
    root.classList.add('lx-js')

    const nodes = Array.from(document.querySelectorAll(selector))
    if (!nodes.length) return undefined

    // Without IntersectionObserver, everything is simply visible.
    if (typeof IntersectionObserver === 'undefined') return undefined

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return
          entry.target.classList.add('lx-reveal--in')
          entry.target.classList.remove('lx-reveal--pending')
          observer.unobserve(entry.target)
        })
      },
      { threshold, rootMargin },
    )

    nodes.forEach((node) => {
      const rect = node.getBoundingClientRect()
      const isBelowFold = rect.top > window.innerHeight * 0.9
      if (isBelowFold) {
        node.classList.add('lx-reveal--pending')
        observer.observe(node)
      } else {
        // Already in view — visible from the start, never hidden.
        node.classList.add('lx-reveal--in')
      }
    })

    return () => observer.disconnect()
  }, [selector, threshold, rootMargin])
}
