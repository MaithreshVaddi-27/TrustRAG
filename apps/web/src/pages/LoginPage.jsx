import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Eye, EyeOff, AlertTriangle, Check } from 'lucide-react'
import AuthLayout from '@/layouts/AuthLayout'
import { authService } from '@/services/auth'
import { ThinkingOrbs } from '@/components/workbench/ThinkingOrbs'

export default function LoginPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  // The register page sends the reader here when the account was created but
  // the automatic sign-in did not happen. It used to carry the flag and
  // nobody read it.
  const justRegistered = params.get('registered') === '1'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authService.login(email, password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Sign in" subtitle="Access your AI reliability workbench">
      <form onSubmit={handleSubmit} className="space-y-4" id="login-form">
        {error && (
          <div className="lx-alert lx-alert--error" role="alert">
            <AlertTriangle size={14} strokeWidth={1.75} aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        {justRegistered && !error && (
          <div className="lx-alert lx-alert--info" role="status">
            <Check size={14} strokeWidth={2} aria-hidden="true" />
            <span>Your account was created. Sign in to continue.</span>
          </div>
        )}

        {loading && (
          <div className="lx-alert lx-alert--info" role="status">
            <ThinkingOrbs size="sm" />
            <span>Signing in…</span>
          </div>
        )}

        <div className="lx-field">
          <label className="lx-field__label" htmlFor="login-email">
            Email
          </label>
          <input
            id="login-email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="lx-field__input"
          />
        </div>

        <div className="lx-field">
          <label className="lx-field__label" htmlFor="login-password">
            Password
          </label>
          <div className="lx-field__wrap">
            <input
              id="login-password"
              name="password"
              type={showPw ? 'text' : 'password'}
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="lx-field__input lx-field__input--with-affix"
            />
            <button
              type="button"
              onClick={() => setShowPw((v) => !v)}
              className="lx-field__affix"
              aria-label={showPw ? 'Hide password' : 'Show password'}
              aria-pressed={showPw}
            >
              {showPw ? (
                <EyeOff size={15} strokeWidth={1.5} aria-hidden="true" />
              ) : (
                <Eye size={15} strokeWidth={1.5} aria-hidden="true" />
              )}
            </button>
          </div>
        </div>

        <button type="submit" disabled={loading} id="login-submit" className="lx-btn lx-btn--primary lx-btn--block lx-btn--large">
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      <p className="lx-auth__foot">
        No account?{' '}
        <Link to="/register">Create one</Link>
      </p>
    </AuthLayout>
  )
}
