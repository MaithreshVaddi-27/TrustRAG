import { Link } from 'react-router-dom'
import { Database, ArrowRight } from 'lucide-react'
import { shortModelId } from '@/lib/modelLabels'

/**
 * WorkspacePanel — the collections the corpus is made of.
 *
 * A specification table: collection, documents, vector space, last run.
 * A bare count of knowledge bases says nothing about whether the corpus is
 * ready to answer questions; the document count, the pinned embedding
 * model and the time of the last run say everything.
 */
export function WorkspacePanel({ kbs = [], lastRunByKb = {} }) {
  if (kbs.length === 0) {
    return (
      <section className="lx-panel-block" aria-labelledby="workspace-heading">
        <div className="lx-panel-block__head">
          <h2 id="workspace-heading" className="lx-panel-block__title flex items-center gap-2">
            <Database size={15} strokeWidth={1.5} aria-hidden="true" className="text-silver-500" />
            Workspace
          </h2>
        </div>
        <div className="lx-panel-block__body">
          <div className="lx-empty">
            <Database size={22} strokeWidth={1.5} className="lx-empty__icon" aria-hidden="true" />
            <p className="lx-empty__title">No collections yet</p>
            <p className="lx-empty__body">
              Create a collection, upload documents, and the corpus becomes
              queryable.
            </p>
            <Link to="/knowledge-bases" className="lx-btn lx-btn--primary">
              Create a collection
              <ArrowRight size={13} strokeWidth={1.75} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="lx-panel-block" aria-labelledby="workspace-heading">
      <div className="lx-panel-block__head">
        <h2 id="workspace-heading" className="lx-panel-block__title flex items-center gap-2">
          <Database size={15} strokeWidth={1.5} aria-hidden="true" className="text-silver-500" />
          Workspace
        </h2>
        <span className="lx-micro">
          {kbs.length} {kbs.length === 1 ? 'collection' : 'collections'}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="lx-table">
          <thead>
            <tr>
              <th scope="col">Collection</th>
              <th scope="col" className="lx-table__num">
                Documents
              </th>
              <th scope="col">Vector space</th>
              <th scope="col">Last run</th>
              <th scope="col">
                <span className="lx-sr-only">Open</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {kbs.map((kb) => {
              const lastRun = lastRunByKb[kb.id]
              return (
                <tr key={kb.id}>
                  <td>
                    <span className="text-silver-100">{kb.name}</span>
                    {kb.description && (
                      <span className="mt-0.5 block text-[var(--size-micro)] text-silver-500">
                        {kb.description}
                      </span>
                    )}
                  </td>
                  <td className="lx-table__num">{kb.document_count ?? 0}</td>
                  <td className="lx-table__id">
                    {kb.embedding_model ? shortModelId(kb.embedding_model) : 'Not pinned'}
                  </td>
                  <td className="lx-table__id">
                    {lastRun ? lastRun.label : 'Never queried'}
                  </td>
                  <td className="lx-table__num">
                    <Link
                      to="/knowledge-bases"
                      className="lx-inline-action justify-end"
                      aria-label={`Open ${kb.name} in the knowledge bases`}
                    >
                      Open
                      <ArrowRight size={11} strokeWidth={1.5} aria-hidden="true" />
                    </Link>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
