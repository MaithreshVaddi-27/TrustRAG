import { Link } from 'react-router-dom'
import { ShieldAlert, ArrowLeft } from 'lucide-react'

export default function NotFoundPage() {
  return (
    <div className="min-h-screen bg-surface-950 flex flex-col items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-surface-900 border border-slate-800 flex items-center justify-center">
          <ShieldAlert size={32} className="text-slate-500" />
        </div>
        <h1 className="text-display-sm text-white mb-3">404</h1>
        <p className="text-body text-slate-400 mb-8">This page doesn't exist or has been moved.</p>
        <Link
          to="/"
          className="btn-primary inline-flex"
        >
          <ArrowLeft size={16} />
          <span>Return Home</span>
        </Link>
      </div>
    </div>
  )
}
