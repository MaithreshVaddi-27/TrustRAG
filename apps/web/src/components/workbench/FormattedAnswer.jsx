import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { clsx } from 'clsx'

/**
 * FormattedAnswer — renders the model's Markdown output as a document.
 *
 * The markdown arrives from a model, so the renderer owns the typography
 * entirely: the prose rules live in `styles/app/markdown.css` rather than
 * in utility classes repeated here. That keeps one reading measure for
 * every answer the product produces.
 */
export function FormattedAnswer({ content, className = '' }) {
  if (!content) return null

  return (
    <div className={clsx('lx-prose', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Model-generated headings are demoted one level so an answer can
          // never inject a second <h1> into a route that already owns one.
          // The deepest level clamps at h4, the last level styled in markdown.css.
          h1: ({ children }) => <h2>{children}</h2>,
          h2: ({ children }) => <h3>{children}</h3>,
          h3: ({ children }) => <h4>{children}</h4>,
          h4: ({ children }) => <h4>{children}</h4>,
          p: ({ children }) => <p>{children}</p>,
          strong: ({ children }) => <strong>{children}</strong>,
          em: ({ children }) => <em>{children}</em>,
          ul: ({ children }) => <ul>{children}</ul>,
          ol: ({ children }) => <ol>{children}</ol>,
          li: ({ children }) => <li>{children}</li>,
          blockquote: ({ children }) => <blockquote>{children}</blockquote>,
          hr: () => <hr />,
          a: ({ children, ...props }) => (
            <a {...props} rel="noopener noreferrer" target="_blank">
              {children}
            </a>
          ),
          code: ({ className: codeClass, children, ...props }) => {
            const isBlock = codeClass?.includes('language-')
            if (!isBlock) {
              return (
                <code className={codeClass} {...props}>
                  {children}
                </code>
              )
            }
            return (
              <pre>
                <code className={codeClass} {...props}>
                  {children}
                </code>
              </pre>
            )
          },
          table: ({ children }) => (
            <div className="lx-prose__table-wrap">
              <table>{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead>{children}</thead>,
          tbody: ({ children }) => <tbody>{children}</tbody>,
          tr: ({ children }) => <tr>{children}</tr>,
          th: ({ children }) => <th>{children}</th>,
          td: ({ children }) => <td>{children}</td>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
