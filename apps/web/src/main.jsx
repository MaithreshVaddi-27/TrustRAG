import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.jsx'
import './index.css'

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

// ── Error boundary — shows a diagnostic message instead of blank white page ─
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }
  static getDerivedStateFromError(error) {
    return { error }
  }
  componentDidCatch(error, info) {
    console.error('[TRUSTRAG] Render error:', error, info.componentStack)
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{
          minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: '#080c16', color: '#e2e8f0', fontFamily: 'monospace', padding: '2rem',
          flexDirection: 'column', gap: '1rem', textAlign: 'center',
        }}>
          <div style={{ fontSize: '1.5rem', color: '#f87171' }}>⚠ TRUSTRAG render error</div>
          <pre style={{ color: '#94a3b8', fontSize: '0.75rem', maxWidth: '600px', textAlign: 'left' }}>
            {this.state.error?.message}
          </pre>
          <button
            onClick={() => this.setState({ error: null })}
            style={{ padding: '0.5rem 1rem', background: '#4f46e5', color: '#fff', border: 'none', borderRadius: '0.5rem', cursor: 'pointer' }}
          >
            Retry
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)
