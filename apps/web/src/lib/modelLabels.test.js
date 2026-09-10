import { describe, it, expect } from 'vitest'
import { shortModelId, providerShortLabel } from './modelLabels'

describe('shortModelId', () => {
  it('strips org, GGUF marker and quant from llama.cpp ids', () => {
    expect(shortModelId('bartowski/EXAONE-3.5-2.4B-Instruct-GGUF:Q4_K_S')).toBe('EXAONE-3.5-2.4B-Instruct')
    expect(shortModelId('ibm-granite/granite-4.2-3b-GGUF:Q4_K_M')).toBe('granite-4.2-3b')
  })

  it('keeps short ollama name:tag ids intact (tag carries size)', () => {
    expect(shortModelId('granite4.2:3b-q4_K_M')).toBe('granite4.2:3b-q4_K_M')
    expect(shortModelId('gemma3:1b')).toBe('gemma3:1b')
  })

  it('shortens embedding and cloud ids to the bare model', () => {
    expect(shortModelId('BAAI/bge-small-en-v1.5')).toBe('bge-small-en-v1.5')
    expect(shortModelId('models/gemini-embedding-001')).toBe('gemini-embedding-001')
    expect(shortModelId('meta/llama-3.3-70b-instruct')).toBe('llama-3.3-70b-instruct')
  })

  it('handles empty input', () => {
    expect(shortModelId('')).toBe('')
    expect(shortModelId(null)).toBe('')
  })
})

describe('providerShortLabel', () => {
  it('normalizes provider variants', () => {
    expect(providerShortLabel('llama_cpp')).toBe('llama.cpp')
    expect(providerShortLabel('llamacpp')).toBe('llama.cpp')
    expect(providerShortLabel('ollama')).toBe('Ollama')
    expect(providerShortLabel('nvidia')).toBe('NVIDIA')
  })
})
