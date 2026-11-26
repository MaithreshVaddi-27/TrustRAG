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
        <main id="main-content" className="lx-auth">
          <div className="lx-auth__column">
            <div className="lx-message lx-message--alarm" role="alert">
              <AlertTriangle size={15} strokeWidth={1.75} className="lx-message__icon" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <h1 className="lx-message__title">Something went wrong in this view</h1>
                <p className="lx-message__body break-words">
                  {this.state.error?.message || 'An unexpected error occurred.'}
                </p>
              </div>
              <button type="button" onClick={this.handleReset} className="lx-btn lx-btn--secondary shrink-0">
                <RefreshCcw size={12} strokeWidth={1.75} aria-hidden="true" />
                Try again
              </button>
            </div>
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() => window.location.assign('/dashboard')}
                className="lx-btn lx-btn--quiet"
              >
                Back to dashboard
              </button>
            </div>
          </div>
        </main>
      )
    }

    return this.props.children
  }
}
