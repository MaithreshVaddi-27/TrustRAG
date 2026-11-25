/**
 * TrustRAG — landing page content.
 *
 * Every string on the marketing page lives here so the components stay
 * presentational and the copy can be reviewed in one place.
 *
 * Split by section. Each module owns one export; `data/index.js` re-exports
 * them for the components that want a single import.
 *
 * Benchmark figures carry their provenance in the `note` field. Every number
 * is measured on the internal reliability fixture documented in
 * `docs/evaluation/`. Do not add a number without a source.
 */

/**
 * The ruled index at the foot of the page.
 *
 * `to` is a route inside the app; `href` is an external address and is
 * rendered as an ordinary link. Every destination below is a place that
 * actually exists.
 */
export const FOOTER = {
  tagline:
    'An open reliability workbench for retrieval-augmented generation. Claim decomposition, NLI audit, and bounded self-healing.',
  groups: [
    {
      title: 'Workbench',
      links: [
        { label: 'Dashboard', to: '/dashboard' },
        { label: 'Playground', to: '/playground' },
        { label: 'Knowledge bases', to: '/knowledge-bases' },
      ],
    },
    {
      title: 'Evidence',
      links: [
        { label: 'Evidence vault', to: '/evidence' },
        { label: 'Claim inspector', to: '/claims' },
        { label: 'Conflicts', to: '/conflicts' },
      ],
    },
    {
      title: 'System',
      links: [
        { label: 'Run history', to: '/dashboard' },
        { label: 'Settings', to: '/settings' },
      ],
    },
  ],
  legal: [
    {
      label: 'Licence',
      href: 'https://github.com/MaithreshVaddi-27/TrustRAG/blob/main/LICENSE',
    },
    {
      label: 'Methodology',
      href: 'https://github.com/MaithreshVaddi-27/TrustRAG/blob/main/docs/evaluation/methodology.md',
    },
    {
      label: 'Source',
      href: 'https://github.com/MaithreshVaddi-27/TrustRAG',
    },
  ],
}
