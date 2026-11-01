import { useState, useCallback, useEffect } from 'react'

const STORAGE_KEY = 'trustrag_sidebar_collapsed'

/**
 * useSidebar - Manages sidebar collapse state with localStorage persistence
 * Called by: AppLayout.jsx
 * No existing file serves this purpose - extracted from AppLayout
 * Reads/writes: localStorage 'trustrag_sidebar_collapsed' (boolean string)
 * User instruction: "continue and Use asynchronous methods for better working with async and await"
 */
export function useSidebar() {
  const [isCollapsed, setIsCollapsed] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === 'true'
    } catch {
      return false
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(isCollapsed))
    } catch (e) {
      console.warn('Could not persist sidebar preference', e)
    }
  }, [isCollapsed])

  const toggleSidebar = useCallback(() => {
    setIsCollapsed(prev => !prev)
  }, [])

  return {
    isCollapsed,
    toggleSidebar,
    // CSS handles width transition: 72px (collapsed) <-> 240px (expanded)
    sidebarWidth: isCollapsed ? 72 : 240,
  }
}