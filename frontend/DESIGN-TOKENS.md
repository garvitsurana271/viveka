# Viveka design tokens (source of truth)

Faithful to `design-export/viveka/project/Viveka.dc.html`. The React/Tailwind build must match these exactly. Two deliberate upgrades vs the export: **SVG icons (Lucide) instead of emoji**, and **darkened muted text** for WCAG AA.

## Color
| Token | Hex | Use |
|---|---|---|
| `bg` | `#efe9dd` | page background (radial: `#f3eee3`→`#efe9dd`→`#e9e2d4`) |
| `surface` | `#fbf8f1` / `#fff` | cards, in-app panels |
| `ink` | `#2a2722` | primary text |
| `ink-strong` | `#1d2422` / `#1d3b37` | headings / brand |
| `teal` (brand) | `#0f6e66` | primary accent, CTAs |
| `teal-deep` | `#0b544d` | teal text on tint |
| `teal-tint` | `#e3efec` (border `#c5ddd7`) | brand chips |
| `line` | `rgba(60,56,50,0.10)` | hairline borders |
| `card-line` | `#e6dfce` / `#ece5d6` | card borders |
| muted | `#6b6459` body-muted · `#8a8170` label — **upgrade `#a99f8c`/`#b6ad9a` → `#857c69`/`#9b9180`** for AA |

### Verdict palette (icon + word + color, never color alone)
| Verdict | word | icon (swap emoji→Lucide) | color | bg | border |
|---|---|---|---|---|---|
| `true` | Likely true | check-circle | `#2e8b57` | `#e7f3ec` | `#c7e3d2` |
| `misleading` | Misleading | alert-triangle | `#9a6708` | `#f9efd6` | `#ecd9a8` |
| `false` | False | x-circle | `#c0392b` | `#fae7e3` | `#eccac3` |
| `human` | Needs human check | user-check / circle-half | `#5350c4` | `#ececfb` | `#d2d2f3` |
| `opinion` | Not a factual claim | message-circle / diamond | `#6b6459` | `#eee9df` | `#ddd5c5` |

Harm levels (Review): high `#c0392b`/`#fae7e3` · med `#9a6708`/`#f9efd6` · low `#2e8b57`/`#e7f3ec`.

## Type
- Headings/display: **Newsreader** (serif), weights 400–600, italic for accent words (e.g. *before*).
- Body/UI: **Hanken Grotesk**, 400–700.
- Hindi/Devanagari: **Noto Sans Devanagari**, 400–600.
- Google Fonts import already in the export `<head>`.

## Radii / shadow / motion
- Radii: chips `999px`, cards `12–18px`, phone panels `14–16px`.
- Shadow: cards `0 10px 34px rgba(40,36,30,0.05)`; CTA `0 8px 22px rgba(15,110,102,0.24)`.
- Keyframes (keep names): `vk-spin`, `vk-fadeup`, `vk-pop`, `vk-dot`, `vk-ring`, `vk-breathe`, `vk-shimmer`. Respect `prefers-reduced-motion`.

## Surfaces & layout
- **Header:** sticky, blurred cream, logo (conic teal/cream disc) + "Viveka" / "Discern before you forward", pill nav (Check/Review/Pulse), "Sources live" dot, language switcher (EN/हिन्दी/Hinglish/Tamil + "19 more").
- **CHECK:** two-col (sticky editorial left: H1 "Separate what's true *before* you forward it." + 5-verdict legend; right: **Android phone frame** containing empty/thinking/verdict states). Mobile-first inside the frame. Stacks at 920px.
- **REVIEW:** `372px` queue + detail (forward, claims, sources checked, "Viveka suggests" + confidence, verdict pills incl. AI-suggested, audit note, Publish → "retrains Viveka, notifies everyone").
- **PULSE:** category filters + sticky stylized India map (positioned hotspots, ring pulse) + ranked rumor list (rank, claim+gloss, verdict chip, regions, sparkline, trend, checks).

## Thinking choreography (CHECK hero — wire to engine stream later)
Steps: 1 Reading the message · 2 Finding the claims (reveals claim chips) · 3 Checking trusted sources (reveals source chips) · 4 Weighing the evidence (confidence bar + note). Mock timings 1050/2250/3650ms → verdict 5500ms; replace with live SSE from the engine.

## Demo content (carry over verbatim)
- Samples: **garlic** (Misleading, 92%, WHO/ICMR/Reuters) and **white-van** (Needs human check, 38%, escalates). Full EN+HI text, claims, sources, meaning, counter-message in the export logic (lines 685–723).
- Review queue: 5 items (white-van, free-laptop phishing, RBI ₹500, warm-water, Monday joke→opinion).
- Pulse: 6 rumors + 9 city hotspots.
