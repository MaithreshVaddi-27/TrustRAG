import { useState, useEffect, useCallback } from 'react'
import { kbService } from '@/services/api'

export function useKnowledgeBaseSelection(initialKbId = '') {
  const [kbId, setKbId] = useState(initialKbId)
  const [knowledgeBases, setKnowledgeBases] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchKnowledgeBases = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await kbService.list()
      setKnowledgeBases(data || [])
      setError(null)
    } catch (err) {
      console.error('Failed to load knowledge bases:', err)
      setError(err.message || 'Failed to load knowledge bases')
      setKnowledgeBases([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchKnowledgeBases()
  }, [fetchKnowledgeBases])

  // Auto-select first KB if none selected
  useEffect(() => {
    if (!kbId && knowledgeBases.length > 0) {
      setKbId(knowledgeBases[0].id)
    }
  }, [knowledgeBases, kbId])

  const selectedKb = knowledgeBases.find(k => k.id === kbId)

  return {
    kbId,
    setKbId,
    knowledgeBases,
    selectedKb,
    isLoading,
    error,
    refetch: fetchKnowledgeBases,
  }
}