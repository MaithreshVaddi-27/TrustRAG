import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { clsx } from 'clsx'

/**
 * FormattedAnswer — Renders LLM output into an ultra-premium, classy executive layout.
 * Replaces raw markdown symbols (**bold**, ### headers, | tables |) with beautiful typography,
 * refined list markers, elegant data tables via remark-gfm, and smooth contrast.
 */
export function FormattedAnswer({ content, className = '' }) {
  if (!content) return null

  return (
    <div className={clsx('formatted-answer space-y-4 text-slate-200 text-sm leading-relaxed', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-lg font-bold text-white tracking-tight pb-2 border-b border-slate-800/80 mt-6 mb-3 flex items-center gap-2">
              <span className="w-1.5 h-4 rounded-full bg-gradient-to-b from-primary-400 to-cyan-400" />
              <span>{children}</span>
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-base font-bold text-slate-100 tracking-tight mt-5 mb-2.5 flex items-center gap-2">
              <span className="w-1 h-3.5 rounded-full bg-cyan-400/80" />
              <span className="text-cyan-200">{children}</span>
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-semibold text-sky-200 tracking-tight mt-4 mb-2">
              {children}
            </h3>
          ),
          p: ({ children }) => (
            <p className="text-slate-200 text-sm leading-relaxed mb-3 last:mb-0">
              {children}
            </p>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-white bg-surface-800/60 px-1 py-0.5 rounded border border-slate-700/40 text-[13.5px]">
              {children}
            </strong>
          ),
          em: ({ children }) => (
            <em className="italic text-slate-300">
              {children}
            </em>
          ),
          ul: ({ children }) => (
            <ul className="space-y-2 my-3 pl-5 list-disc marker:text-cyan-400 text-slate-200 text-sm leading-relaxed">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="space-y-2 my-3 pl-5 list-decimal marker:text-cyan-400 marker:font-mono marker:font-bold text-slate-200 text-sm leading-relaxed">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="pl-1 text-slate-200 text-sm leading-relaxed">
              {children}
            </li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-cyan-500/70 pl-4 py-1 my-3 bg-cyan-950/20 rounded-r-lg text-slate-300 italic">
              {children}
            </blockquote>
          ),
          code: ({ inline, children }) => {
            const isInline = inline ?? false
            if (isInline) {
              return (
                <code className="font-mono text-xs text-cyan-300 bg-surface-900/80 border border-slate-800 px-1.5 py-0.5 rounded">
                  {children}
                </code>
              )
            }
            return (
              <pre className="font-mono text-xs text-slate-300 bg-surface-900/90 border border-slate-800 p-3 rounded-xl overflow-x-auto my-3">
                <code>{children}</code>
              </pre>
            )
          },
          table: ({ children }) => (
            <div className="overflow-x-auto my-5 rounded-xl border border-slate-700/80 bg-surface-900/60 shadow-lg shadow-black/30 backdrop-blur-sm">
              <table className="w-full text-left text-xs border-collapse">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-surface-950/90 text-cyan-300 uppercase tracking-wider font-mono text-[11px] border-b border-slate-700/80">
              {children}
            </thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-slate-800/80 bg-surface-900/40">
              {children}
            </tbody>
          ),
          th: ({ children }) => (
            <th className="px-4 py-3 font-semibold text-slate-200 tracking-wider">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-4 py-3 text-slate-300 leading-relaxed font-normal">
              {children}
            </td>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-cyan-950/20 transition-colors">
              {children}
            </tr>
          ),
          hr: () => (
            <hr className="border-slate-800/80 my-4" />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
