import { useState, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Loader2, Eye, EyeOff, AlertTriangle } from 'lucide-react'
import AuthLayout from '@/layouts/AuthLayout'
import { PasswordRules } from '@/components/auth/PasswordRules'
import { passwordRuleFailures } from '@/lib/passwordRules'
import { authService } from '@/services/auth'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const passwordRef = useRef(null)
  const confirmRef = useRef(null)

  async function handleSubmit(e) {
    e.preventDefault()
    const failures = passwordRuleFailures(password)
    if (failures.length > 0) {
      setError(`The password still needs: ${failures.map((f) => f.label.toLowerCase()).join(', ')}.`)
      passwordRef.current?.focus()
      return
    }
    if (confirmPassword !== password) {
      setError('The two passwords do not match.')
      confirmRef.current?.focus()
      return
    }
    setError('')
    setLoading(true)
    try {
      await authService.register(email, password, fullName)
      // Auto-login after registration
      try {
        await authService.login(email, password)
        navigate('/dashboard')
      } catch {
        navigate('/login?registered=1')
      }
    } catch (err) {
      const msg = err.message || 'Registration failed.'
      setError(
        /already registered|already exists|conflict/i.test(msg)
          ? 'This email is already registered. Sign in to continue.'
          : msg,
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Create account" subtitle="Get started with TrustRAG">
      <form onSubmit={handleSubmit} className="space-y-4" id="register-form">
        {error && (
          <div className="lx-alert lx-alert--error" role="alert">
            <AlertTriangle size={14} strokeWidth={1.75} aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        {loading && (
          <div className="lx-alert lx-alert--info" role="status">
            <Loader2 size={14} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />
            <span>Creating account…</span>
          </div>
        )}

        <div className="lx-field">
          <label className="lx-field__label" htmlFor="reg-name">
            Full name
          </label>
          <input
            id="reg-name"
            name="fullName"
            type="text"
            autoComplete="name"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Your name"
            className="lx-field__input"
          />
        </div>

        <div className="lx-field">
          <label className="lx-field__label" htmlFor="reg-email">
            Email
          </label>
          <input
            id="reg-email"
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
          <label className="lx-field__label" htmlFor="reg-password">
            Password
          </label>
          <div className="lx-field__wrap">
            <input
              id="reg-password"
              name="password"
              ref={passwordRef}
              type={showPw ? 'text' : 'password'}
              autoComplete="new-password"
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
          <PasswordRules value={password} />
        </div>

        <div className="lx-field">
          <label className="lx-field__label" htmlFor="reg-confirm">
            Confirm password
          </label>
          <div className="lx-field__wrap">
            <input
              id="reg-confirm"
              name="confirmPassword"
              ref={confirmRef}
              type={showPw ? 'text' : 'password'}
              autoComplete="new-password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
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

        <button
          type="submit"
          disabled={loading}
          id="register-submit"
          className="lx-btn lx-btn--primary lx-btn--block lx-btn--large"
        >
          {loading && <Loader2 size={14} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />}
          {loading ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="lx-auth__foot">
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </AuthLayout>
  )
}
