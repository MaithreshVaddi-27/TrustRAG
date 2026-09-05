import { Component } from 'react'
import { AlertTriangle, RefreshCcw } from 'lucide-react'

/**
 * ErrorBoundary — catches render errors in a subtree and shows a recovery UI
 * instead of unmounting the entire app (FE-H3).
 *
 * Usage: wrap each route's element so a crash on one page
 * never takes down the whole application shell.
 *
 *   <Route path="/x" element={<RouteBoundary><XPage /></RouteBoundary>} />
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    // Log for diagnostics; never crash the host app.
    console.error('ErrorBoundary caught:', error, info?.componentStack)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[40vh] flex items-center justify-center p-6">
          <div className="max-w-md w-full rounded-2xl border border-red-800/50 bg-red-950/30 p-6 text-center">
            <AlertTriangle className="mx-auto mb-3 text-red-400" size={28} />
            <h2 className="text-sm font-semibold text-red-300 mb-1">
              Something went wrong in this view
            </h2>
            <p className="text-xs text-slate-400 mb-4 break-words">
              {this.state.error?.message || 'An unexpected error occurred.'}
            </p>
            <div className="flex justify-center gap-2">
              <button
                onClick={this.handleReset}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-surface-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-surface-700 transition-colors"
              >
                <RefreshCcw size={12} />
                Try again
              </button>
              <button
                onClick={() => window.location.assign('/dashboard')}
                className="rounded-lg px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
              >
                Back to dashboard
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
