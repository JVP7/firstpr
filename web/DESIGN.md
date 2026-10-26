---
version: alpha
name: firstpr-design
description: A calm, dense tool for picking a first open-source issue. Neutral near-white (light) or near-black (dark) ground, near-black or near-white ink, and one green accent reserved for "why this matches you". System UI type, monospace only for package names. A sparse meteor shower drifts across the page background as the single signature motion.
colors:
  canvas: "#F7F8F7"      # dark: "#0E1013"
  surface: "#FFFFFF"     # dark: "#16191E"
  ink: "#16181D"         # dark: "#E6E8EA"
  ink-muted: "#5B616E"   # dark: "#9BA1AB"
  hairline: "#E3E5E8"    # dark: "#262A31"
  match: "#1A7F37"       # dark: "#3FB950"
  primary: "#16181D"     # dark: "#E6E8EA"
  on-primary: "#FFFFFF"  # dark: "#0E1013"
  error: "#B42318"       # dark: "#F97066"
typography:
  title: { fontFamily: system-ui, fontSize: 24px, fontWeight: 650, lineHeight: 1.2, letterSpacing: -0.01em }
  body: { fontFamily: system-ui, fontSize: 16px, fontWeight: 400, lineHeight: 1.5 }
  ui: { fontFamily: system-ui, fontSize: 14px, fontWeight: 500, lineHeight: 1.4 }
  small: { fontFamily: system-ui, fontSize: 13px, fontWeight: 400, lineHeight: 1.4 }
  package: { fontFamily: ui-monospace, fontSize: 12.5px, fontWeight: 500 }
rounded: { sm: 4px, md: 8px }
spacing: { xs: 4px, sm: 8px, md: 16px, lg: 24px, xl: 48px }
components:
  button-primary: { backgroundColor: "{colors.primary}", textColor: "{colors.on-primary}", typography: "{typography.ui}", rounded: "{rounded.md}", height: 36px }
  card: { backgroundColor: "{colors.surface}", border: "1px solid {colors.hairline}", rounded: "{rounded.md}", padding: 16px }
  package-chip: { typography: "{typography.package}", textColor: "{colors.match}", border: "1px solid currentColor", rounded: "{rounded.sm}" }
---

## Overview
FirstPR is an app screen, not a marketing page. Every screen serves one decision: which issue to
pick up. Dense enough to scan 20 cards, quiet enough to read them.

- One accent, green, and it only ever means "this matches your stack".
- Language is shown with GitHub's own linguist colors (Python #3572A5, JavaScript #f1e05a,
  TypeScript #3178c6), as a 10px dot next to the repo name.
- Icons: Octicons, 16px, ink-muted, only where they carry meaning (issue, star, repo, comment).
- Surfaces are opaque, so the meteor background never sits behind text.

## Colors
Measured contrast: ink on canvas 16.7:1; ink-muted on canvas 5.8:1; match on surface 5.1:1,
on canvas 4.8:1; dark ink 15.5:1, dark muted 7.3:1, dark match 7.5:1. Primary button text 17.8:1.
Headlines are ink, never green.

## Motion
The meteor shower is the only ambient motion. Meteors share one radiant direction per page load
(jitter of a few degrees), one every 1.2-4.5s, occasionally a burst of 2-3, each lasting under
1.2s. A faint static star field sits behind them. With prefers-reduced-motion the static field
stays and meteors stop. The canvas pauses when the tab is hidden. UI transitions: 150ms on color
and opacity only.

## Components
Buttons: primary filled ink, secondary outlined, both 36px tall with a visible focus ring.
Issue card: repo line (lang dot, name, stars), title, up to 3 labels, then the match line
("Uses 4 of your packages:" plus up to 3 package chips and +N).
Every data view has loading (skeleton at final size), empty (why + the action that fixes it)
and error (message + Retry) states.

## Do's and Don'ts
- Do: real numbers ("Uses 4 of your packages"), sentence case, specific button labels.
- Don't: percentages for match strength, stat cards, gradients, glass, emoji, extra accents.

## Responsive behavior
Content column max 880px. At 390px: 16px margins, nav collapses to wordmark plus three short
links, the saved board becomes tabs. No horizontal scroll.

## Logo
Octicons git-pull-request glyph (MIT, GitHub Inc.) in dark-mode match green #3FB950 on an ink tile #16181D,
512 viewBox, corner radius 112. Glyph-on-tile contrast 7.0:1. Source: web/public/logo.svg.

## Known gaps
No custom illustration yet.
