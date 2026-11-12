import { useState } from 'react'
import { Check } from 'lucide-react'
import { CAPABILITIES } from './data/capabilities'

/**
 * CapabilitiesExplorer — four capabilities, one visible at a time.
 *
 * A vertical list on the left selects the capability; the right column shows
 * what it does and the code that does it. No tab panel chrome, no gradient
 * header — the section reads as a specification.
 *
 * The code block scrolls sideways on a narrow screen and holds nothing
 * focusable, so it takes its own tab stop: without one, a keyboard user
 * cannot reach the lines that run past the edge.
 */
export default function CapabilitiesExplorer() {
  const [activeId, setActiveId] = useState(CAPABILITIES[0].id)
  const active = CAPABILITIES.find((cap) => cap.id === activeId) ?? CAPABILITIES[0]
  const ActiveIcon = active.icon

  return (
    <div className="lx-capabilities">
      <div className="lx-capabilities__nav" role="tablist" aria-label="Capabilities">
        {CAPABILITIES.map((cap) => {
          const Icon = cap.icon
          const selected = cap.id === active.id

          return (
            <button
              key={cap.id}
              type="button"
              role="tab"
              id={`cap-tab-${cap.id}`}
              aria-selected={selected}
              aria-controls={`cap-panel-${cap.id}`}
              tabIndex={selected ? 0 : -1}
              className="lx-capability"
              onClick={() => setActiveId(cap.id)}
            >
              <span className="lx-capability__icon">
                <Icon size={16} strokeWidth={1.5} aria-hidden="true" />
              </span>
              <span className="lx-capability__label">{cap.title}</span>
            </button>
          )
        })}
      </div>

      <div
        className="lx-capabilities__panel"
        role="tabpanel"
        id={`cap-panel-${active.id}`}
        aria-labelledby={`cap-tab-${active.id}`}
        tabIndex={0}
      >
        <div className="lx-capability__head">
          <ActiveIcon size={18} strokeWidth={1.5} aria-hidden="true" />
          <div>
            <h3 className="lx-h3">{active.title}</h3>
            <p className="lx-micro lx-capability__tagline">{active.tagline}</p>
          </div>
        </div>

        <p className="lx-body lx-capability__desc">{active.desc}</p>

        <ul className="lx-capability__highlights">
          {active.highlights.map((highlight) => (
            <li key={highlight} className="lx-capability__highlight">
              <Check size={13} strokeWidth={2} aria-hidden="true" />
              <span>{highlight}</span>
            </li>
          ))}
        </ul>

        <pre className="lx-code" tabIndex={0}>
          <code>{active.code}</code>
        </pre>
      </div>
    </div>
  )
}
