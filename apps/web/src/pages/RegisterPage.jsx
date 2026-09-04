import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Loader2, Eye, EyeOff } from 'lucide-react'
import AuthLayout from '@/layouts/AuthLayout'
import { authService } from '@/services/auth'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingTime, setLoadingTime] = useState(0)
  const [error, setError] = useState('')

  useEffect(() => {
    let interval
    if (loading) {
      setLoadingTime(0)
      interval = setInterval(() => {
        setLoadingTime((prev) => prev + 1)
      }, 1000)
    } else {
      setLoadingTime(0)
    }
    return () => clearInterval(interval)
  }, [loading])

  async function handleSubmit(e) {
    e.preventDefault()
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    setError('')
    setLoading(true)
    try {
      await authService.register(email, password, fullName)
      // Auto-login after registration
      await authService.login(email, password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || 'Registration failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Create account" subtitle="Get started with TrustRAG">
      <form onSubmit={handleSubmit} className="space-y-4" id="register-form">
        {error && (
          <div className="rounded-lg border border-red-800/50 bg-red-950/40 px-3 py-2 text-sm text-red-400">
            {error}
          </div>
        )}

        {loading && loadingTime >= 5 && (
          <div className="rounded-lg border border-cyan-800/50 bg-cyan-950/30 px-3 py-2.5 text-xs text-cyan-300 animate-pulse space-y-1">
            <p className="font-semibold flex items-center gap-1.5">
              ⚡ Creating TrustRAG Account ({loadingTime}s elapsed)
            </p>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Setting up your isolated workspace. This usually takes less than a minute.
            </p>
          </div>
        )}

        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-slate-400" htmlFor="reg-name">
            Full name
          </label>
          <input
            id="reg-name"
            type="text"
            autoComplete="name"
            required
            value={fullName}
            onChange={e => setFullName(e.target.value)}
            placeholder="Your name"
            className="w-full bg-surface-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-600 transition-colors"
          />
        </div>

        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-slate-400" htmlFor="reg-email">
            Email
          </label>
          <input
            id="reg-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full bg-surface-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-600 transition-colors"
          />
        </div>

        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-slate-400" htmlFor="reg-password">
            Password
            <span className="text-slate-600 font-normal ml-1">(min. 8 chars)</span>
          </label>
          <div className="relative">
            <input
              id="reg-password"
              type={showPw ? 'text' : 'password'}
              autoComplete="new-password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-surface-800 border border-slate-700 rounded-lg px-3 py-2 pr-10 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-600 transition-colors"
            />
            <button
              type="button"
              onClick={() => setShowPw(v => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
              aria-label={showPw ? 'Hide password' : 'Show password'}
            >
              {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          id="register-submit"
          className="btn-primary w-full flex items-center justify-center gap-2 mt-2"
        >
          {loading && <Loader2 size={14} className="animate-spin" />}
          {loading ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="mt-4 text-center text-xs text-slate-500">
        Already have an account?{' '}
        <Link to="/login" className="text-primary-400 hover:text-primary-300 transition-colors">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  )
}
