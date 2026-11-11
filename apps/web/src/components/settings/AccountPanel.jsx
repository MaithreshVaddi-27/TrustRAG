import { User, Copy, Check, LogOut, ShieldCheck } from 'lucide-react'

/**
 * AccountPanel — who is signed in, and the tenant boundary.
 *
 * The tenant identifier is the security-relevant value on this screen, so it
 * is offered for copying. The partitioning statement below it is the reason
 * the screen exists.
 */
export default function AccountPanel({ user, copied, onCopyId, onSignOut }) {
  return (
    <section className="lx-panel-block" aria-labelledby="account-heading">
      <div className="lx-panel-block__head">
        <h2 id="account-heading" className="lx-panel-block__title flex items-center gap-2">
          <User size={16} strokeWidth={1.5} aria-hidden="true" />
          Account and multi-tenant isolation
        </h2>
        <button type="button" onClick={onSignOut} className="lx-btn lx-btn--alarm">
          <LogOut size={13} strokeWidth={1.75} aria-hidden="true" />
          <span>Sign out</span>
        </button>
      </div>

      <div className="lx-panel-block__body">
        <dl className="lx-deflist">
          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Authenticated account</dt>
            <dd className="lx-deflist__value">{user?.email || 'Active user'}</dd>
          </div>

          <div className="lx-deflist__row">
            <dt className="lx-deflist__key">Tenant ID</dt>
            <dd className="lx-deflist__value flex items-center gap-2">
              <span className="truncate">{user?.id || 'Not available'}</span>
              {user?.id && (
                <button
                  type="button"
                  onClick={onCopyId}
                  className="lx-icon-btn h-7 w-7 shrink-0"
                  title="Copy tenant ID"
                  aria-label="Copy tenant ID"
                >
                  {copied ? (
                    <Check size={13} strokeWidth={2} className="text-silver-200" aria-hidden="true" />
                  ) : (
                    <Copy size={13} strokeWidth={1.5} aria-hidden="true" />
                  )}
                </button>
              )}
            </dd>
          </div>
        </dl>
      </div>

      <div className="lx-panel-block__foot">
        <p className="lx-micro flex items-start gap-2">
          <ShieldCheck size={14} strokeWidth={1.75} className="mt-0.5 shrink-0 text-silver-500" aria-hidden="true" />
          <span>
            Strict tenant partitioning is active. Knowledge base records,
            decomposed claims, retrieved evidence and Qdrant vector points are
            filtered by your tenant ID. Cross-tenant access is refused at the
            API gateway and the database layer.
          </span>
        </p>
      </div>
    </section>
  )
}
