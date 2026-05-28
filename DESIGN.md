# Design System -- ERGO-PLUS Seating Concepts

## Product Context
- **What this is:** Marketing and information website for therapeutic seating solutions
- **Who it's for:** People with physical disabilities (MS, ALS, scoliosis, dwarfism, amputation), their families, therapists, and cost carriers (Krankenkassen)
- **Space/industry:** German healthcare / rehabilitation aids (Hilfsmittelversorgung)
- **Project type:** Marketing site with informational blog, FAQ, and company profile pages
- **Competitors:** vela-stuhl.de, thomashilfen.de, pohlig.net, pflege-sessel.de
- **Positioning:** Specialist, not Sanitatshaus. Human warmth over clinical sterility.

## Aesthetic Direction
- **Direction:** Refined Professional with warm human touch
- **Decoration level:** Intentional -- subtle background gradients, card shadows, no visual clutter
- **Mood:** Trustworthy and competent, but approachable. Not a hospital brochure, not a startup landing page. The visual language says "we understand your situation, and we have the expertise to help."
- **Memorable thing:** Teal CTAs on blue-gray backgrounds. No competitor in the space uses this split. Instant recognition.
- **Reference sites:** vela-stuhl.de (clean but generic), thomashilfen.de (corporate reha), pohlig.net (clinical)

## Typography
- **Display/Hero:** Figtree (800, 700, 600) -- geometric humanist sans with personality. Differentiator: no competitor uses a font with this much character.
- **Body:** Noto Sans (400, 500, 600, 700) -- excellent readability, wide language support, pairs well with Figtree's geometry.
- **UI/Labels:** Figtree (600, 700) for buttons, badges, nav items. Noto Sans (600) for form labels.
- **Data/Tables:** Noto Sans with tabular-nums for any numerical data.
- **Code:** Not applicable (no code display on this site).
- **Loading:** Google Fonts CDN with preconnect. Only load needed weights.
  ```html
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Figtree:wght@300;500;600;700;800&family=Noto+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />
  ```
- **Scale:**
  | Token | Size | Weight | Use |
  |-------|------|--------|-----|
  | 5xl | 3rem / 48px | Figtree 800 | Hero headline |
  | 4xl | 2.25rem / 36px | Figtree 700 | Page titles |
  | 3xl | 1.875rem / 30px | Figtree 700 | Section headings |
  | 2xl | 1.5rem / 24px | Figtree 600 | Subsection headings |
  | xl | 1.25rem / 20px | Noto 500 | Card titles, large body |
  | lg | 1.125rem / 18px | Noto 400 | Lead paragraphs |
  | base | 1rem / 16px | Noto 400 | Body text |
  | sm | 0.875rem / 14px | Noto 400-500 | Captions, metadata |
  | xs | 0.75rem / 12px | Noto 400 | Fine print, labels |

## Color

- **Approach:** Balanced -- primary blue + teal secondary, with amber for highlights. Color has clear semantic roles.

### Core Palette

| Token | Hex | Role |
|-------|-----|------|
| `--c-primary` | #1a5276 | Brand blue. Headings, nav, trust signals. |
| `--c-primary-dk` | #154360 | Hover states, dark accents. |
| `--c-primary-lt` | #d6eaf8 | Light backgrounds, info alerts, badges. |
| `--c-teal` / `--c-cta` | #148f77 | CTA buttons, links, success accents. THE differentiator. |
| `--c-teal-dk` | #117a65 | CTA hover state. |
| `--c-teal-lt` | #d1f2eb | Teal badges, light teal backgrounds. |
| `--c-amber` / `--c-accent` | #d68910 | Warnings, highlights, stat numbers. |
| `--c-amber-lt` | #fef3cd | Warning alert background. |

### Neutrals

| Token | Hex | Role |
|-------|-----|------|
| `--c-bg` | #f0f5fa | Page background (blue-tinted gray). |
| `--c-bg2` | #ffffff | Card/surface background. |
| `--c-bg3` | #f7fafc | Alternate section background. |
| `--c-text` | #1a2a3a | Primary text (near-black with blue tint). |
| `--c-text-md` | #2c3e50 | Secondary text. |
| `--c-text-soft` | #5d6d7e | Tertiary text, placeholders. |
| `--c-border` | #c8dae8 | Default borders. |
| `--c-border-lt` | #e2ecf4 | Light borders, dividers. |

### Semantic

| Token | Hex | Use |
|-------|-----|-----|
| `--c-success` | #27ae60 | Success alerts, confirmations. |
| `--c-warning` | #d68910 | Warning alerts (same as amber). |
| `--c-error` | #c0392b | Error alerts, validation. |
| `--c-info` | #2e86c1 | Info alerts, tooltips. |

### Dark Mode Strategy
Redesign surfaces to deep blue-grays (#0f1923 base). Desaturate accent colors 10-20%. Primary becomes #5dade2 (lighter blue). Teal becomes #48c9b0. Maintain contrast ratios above WCAG AA.

## Spacing
- **Base unit:** 8px
- **Density:** Comfortable -- generous whitespace for older/disabled target audience.
- **Scale:**

| Token | Value | Use |
|-------|-------|-----|
| `--sp-2xs` | 2px | Hairline gaps, icon padding |
| `--sp-xs` | 4px | Tight inline spacing |
| `--sp-sm` | 8px | Default gap, small padding |
| `--sp-md` | 16px | Card padding, form gaps |
| `--sp-lg` | 24px | Section inner padding |
| `--sp-xl` | 32px | Section padding, large gaps |
| `--sp-2xl` | 48px | Between major sections |
| `--sp-3xl` | 64px | Top-level section padding |

## Layout
- **Approach:** Grid-disciplined with creative hero
- **Grid:** Single-column mobile, 2-column tablet, asymmetric hero + 3-column content grid desktop
- **Max content width:** 1200px (with 1100px for text-heavy sections)
- **Border radius hierarchy:**

| Token | Value | Use |
|-------|-------|-----|
| `--radius-sm` | 10px | Inputs, small cards, badges |
| `--radius` | 14px | Default cards, containers |
| `--radius-lg` | 20px | Large cards, sections |
| `--radius-xl` | 28px | Hero sections, modals |
| pill | 50px | Buttons, eyebrow badges |

## Shadows

All shadows use blue-tinted rgba (26, 82, 118) to match the primary color:

| Token | Value | Use |
|-------|-------|-----|
| `--shadow-xs` | `0 1px 3px rgba(26,82,118,.06), 0 1px 2px rgba(26,82,118,.04)` | Subtle lift, badges |
| `--shadow-sm` | `0 2px 8px rgba(26,82,118,.07), 0 4px 16px rgba(26,82,118,.05)` | Cards resting state |
| `--shadow-md` | `0 4px 16px rgba(26,82,118,.08), 0 12px 40px rgba(26,82,118,.06)` | Card hover, dropdowns |
| `--shadow-lg` | `0 8px 30px rgba(26,82,118,.10), 0 24px 60px rgba(26,82,118,.08)` | Modals, hero elements |

## Motion
- **Approach:** Intentional -- reveal animations on scroll, smooth hover transitions. Never jarring.
- **Easing:**
  - Enter: `cubic-bezier(.22, 1, .36, 1)` (spring-like ease-out)
  - Exit: `ease-in`
  - Move: `ease-in-out`
- **Duration:**
  | Token | Range | Use |
  |-------|-------|-----|
  | micro | 50-100ms | Hover color changes, focus rings |
  | short | 150-250ms | Button transitions, card lifts |
  | medium | 250-400ms | Scroll reveals, section entrances |
  | long | 400-700ms | Hero entrance sequence, page transitions |
- **Scroll reveals:** Elements fade in + translate 30px upward on viewport entry. Staggered 80ms between siblings.
- **Reduced motion:** Respect `prefers-reduced-motion: reduce`. Disable transforms, keep opacity fades at 200ms max.

## Accessibility Notes
- All text meets WCAG AA contrast (4.5:1 for body, 3:1 for large text).
- Focus rings: 3px solid teal with teal-lt background offset.
- Touch targets: minimum 44x44px for all interactive elements.
- Font sizes never below 14px for body content (target audience includes elderly/visually impaired).

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-28 | Initial design system created | Formalized existing site design after competitive analysis of vela-stuhl.de, thomashilfen.de, pohlig.net, pflege-sessel.de |
| 2026-05-28 | Keep Figtree + Noto Sans | Already strongest typography in the competitive space. No reason to change. |
| 2026-05-28 | Teal CTA as key differentiator | No competitor uses teal for actions. Instant visual recognition. |
| 2026-05-28 | Blue-tinted shadows | Cohesive with primary palette. Warmer than pure gray shadows. |
| 2026-05-28 | Comfortable spacing density | Target audience (elderly, disabled) benefits from generous whitespace. |
