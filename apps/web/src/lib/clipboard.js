/**
 * copyToClipboard — safe clipboard write for all contexts (FE-M4).
 *
 * `navigator.clipboard` only exists in secure contexts (https/localhost) and
 * can reject when the document lacks focus. This helper guards every path and
 * falls back to the legacy execCommand approach, so copy buttons degrade
 * gracefully instead of throwing unhandled promise rejections.
 *
 * @param {string} text
 * @returns {Promise<boolean>} true if the copy likely succeeded
 */
export async function copyToClipboard(text) {
  if (text == null) return false
  const value = String(text)

  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value)
      return true
    }
  } catch {
    // Fall through to legacy path (permissions denied, unfocused document, etc.)
  }

  // Legacy fallback for non-secure contexts
  try {
    const ta = document.createElement('textarea')
    ta.value = value
    ta.setAttribute('readonly', '')
    ta.style.position = 'fixed'
    ta.style.left = '-9999px'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch {
    return false
  }
}
