import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MotionConfig, useReducedMotion } from 'motion/react'
import App from './App.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import './index.css'

/* eslint-disable react-refresh/only-export-components */

// ── TanStack Query client ─────────────────────────────────────────────────
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60 * 1000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
})

// Root wrapper that applies Apple Design reduced-motion preference globally
function MotionProvider({ children }) {
  const reducedMotion = useReducedMotion()
  return (
    <MotionConfig
      reducedMotion={reducedMotion}
      transition={reducedMotion ? { type: 'tween', duration: 0.2, ease: 'easeOut' } : { type: 'spring', bounce: 0, duration: 0.35 }}
    >
      {children}
    </MotionConfig>
  )
}

// ── Error boundary lives in components/ErrorBoundary.jsx (single implementation) ─

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <MotionProvider>
            <App />
          </MotionProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)
