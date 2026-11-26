/**
 * The password's requirements, in one place.
 *
 * The register form used to carry a sentence describing five rules and
 * check them only after the form was submitted, so a reader who missed
 * one learned about it by failing. The same five rules are now a list,
 * and the list reports itself as it is met.
 */
export const PASSWORD_RULES = [
  { id: 'length', label: 'At least 12 characters', test: (value) => value.length >= 12 },
  { id: 'upper', label: 'An uppercase letter', test: (value) => /[A-Z]/.test(value) },
  { id: 'lower', label: 'A lowercase letter', test: (value) => /[a-z]/.test(value) },
  { id: 'digit', label: 'A digit', test: (value) => /\d/.test(value) },
  {
    id: 'symbol',
    label: 'A symbol',
    test: (value) => /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(value),
  },
]

/** The rules a password has not met yet. */
export function passwordRuleFailures(value) {
  return PASSWORD_RULES.filter((rule) => !rule.test(value ?? ''))
}
