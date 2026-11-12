import {
  Brain,
  Database,
  FileSearch,
  GitMerge,
  LayoutDashboard,
  Settings,
  Zap,
} from 'lucide-react'

/**
 * The application's navigation, in one place.
 *
 * The sidebar and the mobile drawer are the same list rendered twice — in
 * different shapes, for different widths. When they each carried their own
 * copy of the array they drifted, and a new route had to be remembered
 * twice. One source, two renderings.
 *
 * The groups are named because the separators alone do not tell a reader
 * why "Evidence" is in the middle and "Settings" is at the bottom.
 */
export const NAV_GROUPS = [
  {
    id: 'work',
    label: 'Workbench',
    items: [
      { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
      { label: 'Playground', to: '/playground', icon: Zap, meta: 'Live' },
    ],
  },
  {
    id: 'corpus',
    label: 'Corpus',
    items: [
      { label: 'Knowledge bases', to: '/knowledge-bases', icon: Database },
      { label: 'Evidence', to: '/evidence', icon: FileSearch },
      { label: 'Claims', to: '/claims', icon: Brain },
      { label: 'Conflicts', to: '/conflicts', icon: GitMerge },
    ],
  },
  {
    id: 'system',
    label: 'System',
    items: [{ label: 'Settings', to: '/settings', icon: Settings }],
  },
]

/**
 * Initials for the account chip.
 *
 * Derived from the display name when there is one, otherwise from the local
 * part of the email address — never from the first two characters of the
 * address, which produces things like "AU" for audit@example.com.
 */
export function accountInitials(user) {
  const name = (user?.name || '').trim()
  if (name) {
    const parts = name.split(/[\s._-]+/).filter(Boolean)
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    }
    return name.slice(0, 2).toUpperCase()
  }

  const email = (user?.email || '').trim()
  const local = email.split('@')[0] || ''
  const parts = local.split(/[._-]+/).filter(Boolean)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  }
  return (local.slice(0, 2) || 'TR').toUpperCase()
}

/** The account's display name, falling back to the email address. */
export function accountLabel(user) {
  const name = (user?.name || '').trim()
  if (name) return name
  const email = (user?.email || '').trim()
  if (!email) return 'Signed in'
  return email
}
