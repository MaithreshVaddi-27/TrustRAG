# TrustRAG — brand mark · Overlap

**Idea.** The claim is a solid Chrome Silver disc; the corpus is a Chrome Silver ring.
Exactly half the claim is grounded inside the evidence, and the single Laser Crimson point
sits at the centre of that supported half. Support is the overlap; everything outside it is
unsupported.

The mark replaces the earlier rounded-square seal. It keeps the house rules: flat linework,
Obsidian substrate, Chrome Silver as the voice, and Laser Crimson exactly once — at the verdict.

## Files

| File | Use |
|---|---|
| `final-symbol.svg` | Master symbol (256×256 viewBox, transparent) |
| `lockup-horizontal.svg` | Symbol + wordmark, horizontal |
| `lockup-stacked.svg` | Symbol above wordmark, stacked |
| `kit/` | Export set: black / white / mono variants, square, favicon, app icon, PNG + web/PWA icons |
| `brand-board.html` · `brand-board.png` | Usage board (dark) |

In the product the mark is rendered by
`apps/web/src/components/common/TrustRagLogo.jsx` (`TrustRagEmblem`). Web icons live in
`apps/web/public/icons/` and are wired through `index.html` and `public/manifest.json`.

## Colour

| Role | Value |
|---|---|
| Ground | `#080808` obsidian |
| Claim disc | `#cdcbcA` chrome silver |
| Corpus ring | `#a3a2a0` |
| Verdict point (once) | `#d41514` laser crimson |

One-colour variants: black `#000000`, white `#ffffff`, mono `#cdcbcA`.

## Rules

- **Clear space** — a margin equal to the crimson point's diameter (22 units) on every side.
- **Minimum size** — mark 20 px; app-tile / favicon 16 px. Below 20 px use the tile, not the bare mark.
- **Backgrounds** — obsidian and graphite surfaces. On light grounds use the black or mono variant.
- **Never** — rotate, tilt, outline, add gradients/glows/shadows, recolour the disc or ring, or move the crimson point.
- **Type** — wordmark is the system sans stack, weight 500, tracking −0.02em. Outline it before embedding elsewhere.

## Notes

- At 16 px the full geometry softens; the shipped favicon uses the app-tile form, which keeps a
  legible silhouette. A denser small-size cut can be drawn from the master if a sub-20 px surface appears.
- Fonts are the system stack only (air-gapped installs ship no font payload), so the lockups use
  `<text>` rather than outlined paths; outline before use on a platform that needs embedded type.
