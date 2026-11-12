import { Check, Circle } from 'lucide-react'
import { PASSWORD_RULES } from '@/lib/passwordRules'

/**
 * PasswordRules — the requirement list, reporting what is still missing.
 *
 * An unmet rule is not an alarm: it is a requirement, and it is written in
 * the same quiet silver as everything else on this screen. Only the rule
 * that has been met is marked.
 */
export function PasswordRules({ value }) {
  return (
    <ul className="lx-rules" aria-label="Password requirements">
      {PASSWORD_RULES.map((rule) => {
        const met = rule.test(value ?? '')
        return (
          <li
            key={rule.id}
            className={`lx-rules__item${met ? ' lx-rules__item--met' : ''}`}
          >
            {met ? (
              <Check size={12} strokeWidth={2} aria-hidden="true" />
            ) : (
              <Circle size={8} strokeWidth={1.75} aria-hidden="true" />
            )}
            <span>{rule.label}</span>
            <span className="lx-sr-only">
              {met ? ' — met' : ' — not met yet'}
            </span>
          </li>
        )
      })}
    </ul>
  )
}
