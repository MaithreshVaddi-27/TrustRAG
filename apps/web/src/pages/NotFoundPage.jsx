import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

export default function NotFoundPage() {
  return (
    <main className="lx-auth">
      <div className="text-center max-w-md">
        <p className="lx-micro">Error 404</p>

        <h1 className="lx-display-sm mt-3">This page does not exist.</h1>

        <p className="lx-body mt-4">
          The address may be out of date, or the page may have been moved.
        </p>

        <div className="mt-8 flex items-center justify-center">
          <Link to="/" className="lx-btn lx-btn--primary">
            <ArrowLeft size={15} strokeWidth={1.5} aria-hidden="true" />
            <span>Back to the overview</span>
          </Link>
        </div>
      </div>
    </main>
  )
}
