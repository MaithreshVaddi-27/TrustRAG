/**
 * modelLabels — precise, untruncated display labels for model/engine pills.
 *
 * Backend model ids are filesystem-style paths (`org/Name-GGUF:QUANT`) that
 * overflow pills and cards. These helpers produce short human labels while
 * callers keep the full id in `title` tooltips so nothing is lost.
 */

export function shortModelId(id) {
  if (!id) return ''
  const raw = String(id)
  // Ollama `name:tag` ids are already short — the tag carries the size.
  if (!raw.includes('/')) return raw
  let s = raw.split('/').pop()
  s = s.split(':')[0] // drop quant suffix (:Q4_K_M)
  s = s.replace(/-GGUF$/i, '') // drop GGUF marker, keep Instruct/size
  return s || raw
}

export function providerShortLabel(provider) {
  const p = (provider || '').toLowerCase()
  if (p === 'ollama') return 'Ollama'
  if (p === 'llama_cpp' || p === 'llamacpp') return 'llama.cpp'
  if (p === 'gemini' || p === 'google_genai') return 'Gemini'
  if (p === 'nvidia' || p === 'nim') return 'NVIDIA'
  if (p === 'huggingface') return 'Local BGE'
  return provider || 'Local'
}
