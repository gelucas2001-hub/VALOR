---
name: VALOR
description: A quant's instrument for weighing model probability against market odds — the gap between them is the whole product.
colors:
  ink: "#0F141A"
  ink-2: "#141C24"
  surface: "#19222B"
  surface-2: "#202B36"
  line: "#2A3641"
  line-soft: "#212C36"
  paper: "#E9E7E2"
  muted: "#8496A5"
  muted-2: "#7A8D9B"
  assayers-gold: "#E0A93C"
  assayers-gold-deep: "#8A6415"
  assayers-gold-wash: "rgba(224,169,60,.10)"
  deep-oxide: "#C4593F"
  deep-oxide-wash: "rgba(196,89,63,.10)"
  deep-oxide-text: "#E6BCB1"
  deep-petrol: "#4A8395"
  deep-petrol-wash: "rgba(74,131,149,.12)"
  deep-petrol-text: "#BBD6DE"
  ink-on-gold: "#171106"
  ink-on-gold-soft: "rgba(23,17,6,.65)"
typography:
  display:
    fontFamily: "IBM Plex Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "34px"
    fontWeight: 500
    lineHeight: 1.05
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1.2
    fontVariation: "wdth 106, wght 700"
  title:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "16.5px"
    fontWeight: 600
    lineHeight: 1.28
    fontVariation: "wdth 104, wght 600"
  body:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "15px"
    fontWeight: 450
    lineHeight: 1.45
    fontVariation: "wdth 100, wght 450"
  label:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "10px"
    fontWeight: 600
    letterSpacing: "0.16em"
    fontVariation: "wdth 115, wght 600"
  mono:
    fontFamily: "IBM Plex Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "15px"
    fontWeight: 500
    fontFeature: "tnum 1"
rounded:
  sm: "6px"
  md: "10px"
  pill: "100px"
spacing:
  pad: "16px"
components:
  button-primary:
    backgroundColor: "{colors.assayers-gold}"
    textColor: "#171106"
    rounded: "{rounded.sm}"
    padding: "10px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.sm}"
    padding: "10px"
  chip:
    backgroundColor: "{colors.ink-2}"
    textColor: "{colors.muted}"
    rounded: "{rounded.pill}"
    padding: "6px 12px"
  chip-active:
    backgroundColor: "{colors.assayers-gold-wash}"
    textColor: "{colors.assayers-gold}"
    rounded: "{rounded.pill}"
    padding: "6px 12px"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "13px 14px"
  card-value:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "13px"
  input:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.sm}"
    padding: "7px 9px"
---

# Design System: VALOR

## Overview

**Creative North Star: "The Quant Copilot & Precision Advisor"**

VALOR es un **Asesor y Copiloto Inteligente de Apuestas** diseñado con la disciplina de un instrumento analítico. No es un casino ni un canal de tipsters con promesas vacías: es una herramienta que traduce modelos matemáticos complejos (Dixon-Coles, EV, Kelly, matrices conjuntas) en **veredictos claros, recomendaciones guiadas y advertencias de riesgo**.

La paleta se rige por un sistema estricto de tres metales: superficies en petróleo profundo (`#0F141A`), **latón/oro** (`#E0A93C`) para marcar dónde el modelo supera al mercado (*Valor Detectado*), y **óxido** (`#C4593F` / `#E6BCB1`) para advertir dónde el mercado tiene ventaja (*Desventaja Matemática / Riesgo no compensado*). Un tercer tono analítico, **petróleo** (`#4A8395`), marca líneas justas y puntos de referencia neutrales.

**Características Clave:**
- **Sistema semántico de tres metales:** Oro = valor real comprobado, Óxido = desventaja matemática/riesgo no compensado, Petróleo = línea justa/neutral. Sin semáforos genéricos ni emojis artificiales.
- **Diagnósticos Honestos:** Veredictos claros que comunican el nivel de ventaja y la confianza del backtest sin simular certezas absolutas.
- **Tipografía disciplinada:** Archivo (variable sans) para palabras y explicaciones; IBM Plex Mono (tabular nums) exclusivamente para cifras numéricas (cuotas, EV, xG, Kelly).
- **Layout Mobile-First con contención Desktop:** Optimizado para uso táctil fluido en PWA y centrado elegantemente (`max-width: 560px`) en pantallas de escritorio.

## Colors

The palette reads as petrol-black metal with two accent metals struck into it — warm gold for value, cold oxide for danger — and a third, quieter petrol accent held in reserve for neutral facts.

### Primary
- **Assayer's Gold** (`#E0A93C`): The single most important color in the system. Marks wherever the model's calculated edge beats the market — the opportunity block, value-state market cards, active filter chips, primary buttons, the "on" state of nearly every toggle. A deeper variant, **Assayer's Gold, Deep** (`#8A6415`), is reserved for borders and gradient edges on value-state containers, never for text or fills at that darker value. Where gold is the *background* (active day pill, primary button), text sits in **Ink on Gold** (`#171106`) / **Ink on Gold, Soft** (`rgba(23,17,6,.65)`) rather than the page's own ink tone, since the page's `--ink` doesn't have enough contrast against gold to read as intentional.

### Secondary
- **Deep Oxide** (`#C4593F`): The warning metal. Marks false value — where the model's number looks good but a correlation or de-vig check says it wouldn't survive contact with reality — and negative figures (losses, negative EV) at large display sizes (the 34px opportunity figure). Below 24px, raw Deep Oxide falls under WCAG AA's 4.5:1 text-contrast floor on these dark surfaces (~3.7–4.3:1 measured); smaller negative figures (market grids, ledger stats, tables) use **Deep Oxide, Text** (`#E6BCB1`, ~9:1) instead — the same lightened tone the warning banner already used.

### Tertiary
- **Deep Petrol** (`#4A8395`): The neutral analytical accent. Used only for the "fair odds" mark on the gap bar and informational (non-warning) callouts — it never competes with gold or oxide for the user's attention because it never signals a verdict, only a reference point. **Deep Petrol, Text** (`#BBD6DE`) is the readable-on-dark variant used for `.warn.info` banner copy.

### Neutral
- **Ink** (`#0F141A`): The base page background — the deepest tone in the system.
- **Ink, Raised** (`#141C24`): One step up — sticky header gradient origin, unselected day pills, input backgrounds.
- **Surface** (`#19222B`): Card and container background — where match cards, market cards, boxes, and sliders sit.
- **Surface, Pressed** (`#202B36`): The `:active` state for cards — the only elevation cue in the system is this one-step tonal shift, not a shadow.
- **Line** (`#2A3641`): Default border color for cards, inputs, and dividers.
- **Line, Soft** (`#212C36`): Quieter divider — used inside accordions and between stacked sections rather than around containers.
- **Paper** (`#E9E7E2`): Primary text color — a warm off-white, never pure white.
- **Muted** (`#8496A5`) / **Muted, Deep** (`#7A8D9B`): Secondary and tertiary text — competition labels, meta rows, eyebrows, placeholder text. Muted, Deep was lightened from an earlier `#5F707E` after a contrast audit found the darker value fell to ~3.1–3.6:1 on Ink and Surface, below the 4.5:1 AA floor for its 9–11px uppercase-label use.

### Named Rules
**The Two-Metal Rule.** Gold and oxide never appear on the same number. A figure is either a real value signal (gold) or a false/negative one (oxide) — never both, never neither when a verdict exists.

**The Rarity Rule.** Gold is reserved for an actual verdict, not for decoration or brand presence. Outside the opportunity block, active states, and CTAs, gold does not appear — its scarcity is what makes it legible as a signal.

**The Text-Safe Variant Rule.** Any accent color used as a *background* or at large display size gets a dedicated `-text` (or `ink-on-*`) variant for smaller text roles, rather than being reused at full saturation below the size where it stops meeting 4.5:1.

## Typography

**Body/Display Font:** Archivo (variable font, `wdth` 62–125, `wght` 400–800), with system-ui fallback.
**Numeric Font:** IBM Plex Mono, with `ui-monospace`/`SFMono-Regular`/`Menlo` fallback.

**Character:** Archivo carries every word in the interface and is tuned per-context via variable-font axes rather than swapping families — tighter widths and heavier weights for labels and headlines, calmer default width and weight for body copy. IBM Plex Mono is reserved entirely for anything that is a number a user needs to compare or trust: odds, EV, probabilities, stats, table figures. The pairing is the visual expression of the product's core move — words explain, numbers decide.

### Hierarchy
- **Display** (500, 34px, line-height 1.05, mono): The EV/opportunity figure at the top of the opportunity block — the single number the whole product exists to produce. The only place a number is sized to dominate the screen.
- **Headline** (700, 22px, line-height 1.2, `wdth` 106): Match detail team names.
- **Title** (600, 16.5–21px, `wdth` 102–125): List-view team names and the brand wordmark.
- **Body** (450, 15px, line-height 1.45, `wdth` 100): Default running text and paragraph content.
- **Label** (600, 10–11px, letter-spacing 0.1–0.16em, uppercase, `wdth` 112–115): Eyebrows, section headers, meta tags, table headers — always uppercase, always wide-tracked.
- **Mono/Numeric** (500, 10.5–15px, tabular-nums): Every odds figure, EV value, stat, table cell, and countdown. Set with `font-feature-settings:"tnum 1"` so columns of figures always align.

### Named Rules
**The Tabular Numerals Rule.** Any digit that represents data — not a label, not a count badge, a *data value* — renders in IBM Plex Mono with tabular figures. Archivo never carries a number the user is meant to compare against another number.

## Layout

Mobile-first and, at present, mobile-only: there is no desktop breakpoint to preserve or diverge from, and any expansion to larger viewports is a genuinely new decision, not a gap to fill by habit. The page is a single scrolling column with a sticky header (day strip, summary ledger, filters) and a fixed bottom tab bar; content padding is a single consistent `16px` (`--pad`) from the page edge, respected by every section. Safe-area insets (`env(safe-area-inset-top/bottom)`) are honored in the header and nav so the installed-PWA chrome never clips content on notched devices. Vertical rhythm between stacked cards runs roughly 9–14px; there is no formal spacing scale beyond the one horizontal padding token — density is kept tight and consistent by convention, not by a token system.

## Elevation & Depth

Revised: the instrument now has physical weight. Every card-level container (`match`, `mkt`, `box`, `log-item`, `sliders`, `matrix`, `combo-rec-card`, `ctx-mini`, `today-top`, `opp`, `ledger`) carries one shared neutral elevation (`--shadow-card`): a hairline inner highlight (top bevel, like machined metal catching light) plus a soft dark drop shadow. This is layered *on top of* the tonal stack and washes from before, not a replacement for them — a card is still identifiable at rest by tone and border; the shadow adds physical lift, not identity. Value-state cards add a second shadow layer, `--shadow-brass`: a solid `Assayer's Gold, Deep` ring, no blur, no color bleed into the shadow itself — a blurred colored halo reads as generic AI-gloss and is explicitly avoided (confirmed against the design detector). Interactive elements get a matching press language: primary cards translate 1px down on `:active`; the primary button scales to `98%` with its inner highlight dimming; pills and tabs drop opacity to `72%`. Focus states use a solid, non-blurred gold ring (`--ring`, `0 0 0 3px`) on every tappable/typeable element — this supersedes the old "no glow, no outline ring" line below; a ring is not a glow, and its absence was an accessibility gap, not a stylistic choice worth keeping.

### Named Rules
**The Ring, Never a Halo Rule.** Any indicator of state — focus, value, emphasis — is a solid-color ring, border, or wash. Blurred, colored (non-neutral) box/text shadows are banned outright regardless of how subtle; they are the single most identifiable AI-generated-UI tell and the design detector flags them by name. Elevation shadows (lift, weight) are always neutral black at low opacity; color signals value through fill/border/wash, never through shadow.

## Shapes

Two radii cover the entire system: `10px` for containers (cards, boxes, the opportunity block, market cards) and `6px` for controls (buttons, inputs, small tags). Fully-rounded pills (`100px`) are reserved for filter chips and the day-selector strip. Borders are always `1px` solid. A handful of small indicator elements (form-result squares, the gap-bar track) use tighter one-off radii in the 2–4px range appropriate to their small size, not a third scale to be reused elsewhere.

### Named Rules
**The Two-Radius Rule.** A new component takes `10px` if it's a container something else lives inside, `6px` if it's a control someone taps or types into. Anything reaching for a third radius value is probably supposed to be a pill or an indicator, not a new scale.

## Components

Buttons, cards, and inputs are spartan and instrument-like: flat, bordered, zero ornament, built to look like panel controls rather than app chrome.

### Buttons
- **Shape:** `6px` radius, full-width by default.
- **Primary:** Assayer's Gold background, near-black text (`#171106`), `10px` padding, uppercase label at wide letter-spacing (0.1em) and a heavy variable weight (`wdth` 112, `wght` 700). A subtle inner top highlight (`--sheen`) plus a neutral (not gold) drop shadow give it a struck-metal feel; on press it scales to `98%` and the highlight dims to `--sheen-soft`.
- **Ghost:** Transparent background, `Line` border, `Muted` text — used for secondary actions next to a primary gold button. No shadow.
- **Disabled:** `35%` opacity, no other treatment change.

### Chips
- **Style:** Fully rounded (`100px`), `Ink, Raised` background, `Line` border, `Muted` text at rest.
- **State (active):** Assayer's Gold wash background, `Assayer's Gold, Deep` border, `Assayer's Gold` text. Used for both filter chips and the day-selector strip's selected day.

### Cards / Containers
- **Corner Style:** `10px` radius.
- **Background:** `Surface`, one tone above the page background.
- **Shadow Strategy:** `--shadow-card` on every container (neutral lift + inner bevel) — see Elevation & Depth. Value-state cards add `--shadow-brass` (solid gold ring, no blur) on top.
- **Border:** `1px solid Line`; value-state cards (a match or market with real edge) switch the border to `Assayer's Gold, Deep` and add a faint gold gradient wash to signal importance.
- **Internal Padding:** `13–14px`.

### Inputs / Fields
- **Style:** `Ink` background (one tone below the card it sits in), `1px` `Line` border, `6px` radius, mono numeral font for odds fields specifically. A **search variant** (player lookup) drops the mono/centered treatment for left-aligned Archivo — it's a name, not a number, and shouldn't dress like one.
- **Focus:** Border shifts to `Assayer's Gold, Deep`, background lightens one tone to `Ink, Raised`, and a solid (non-blurred) gold focus ring (`--ring`) appears — see Elevation & Depth's Ring, Never a Halo rule.

### Recommendation & Context Cards
Three cards exist to move the app from "here's the data" toward "here's what I'd do" without ever crossing into invented certainty:
- **Today's Top** (day list): the single best pick of the day, by name, above the fold — gold-bordered wash identical to a value-state market card, because it *is* one, just promoted to the day level.
- **Context teaser** (match detail): the human analyst's one-line verdict, pulled up from the buried "Datos" tab. Deliberately **not** gold or oxide — those colors are reserved for the model's own verdict, and this is a person's opinion. Flat `Surface`/`Line`, same as any neutral box.
- **Recommended combo**: the system assembles the combination instead of the user picking legs by hand. Same gold-only-if-real-EV discipline as everything else — a recommended combo with no value simply doesn't render, it never appears "recommended" out of politeness. Each leg may carry a small `Deep Petrol` "histórico N%" chip when backtest calibration data exists for that market — absent, not fabricated, when it doesn't.

### Navigation
- Fixed bottom tab bar, 5 equal columns, translucent `Ink` background with backdrop blur, `1px` top border, `--shadow-lift` (neutral) separating it from scrolling content beneath. Icons are 19px stroked outlines; inactive tabs are `Muted, Deep`, the active tab switches icon and label to Assayer's Gold and gets a small solid gold tick above the icon. Respects `env(safe-area-inset-bottom)`.

### The Gap Bar (signature component)
The one custom visual invented for this product, and the closest thing it has to a logo. A single horizontal rail represents 0–100% probability; a thin `Paper` tick marks the model's own number, a thin `Muted` tick marks the bookmaker's implied probability, and a thin `Deep Petrol` tick marks the de-vigged fair line. The filled segment between the book's mark and the model's mark — in gold if the model is ahead, oxide if the market is ahead — is not decoration: it is the literal size of the number the whole product exists to compute. No other element in the interface is allowed to visually compete with this bar for the user's first glance.

## Do's and Don'ts

### Do:
- **Do** keep gold reserved for an actual value verdict — opportunity block, value-state cards/borders, active chips, primary CTAs. Nowhere else.
- **Do** render every data numeral in IBM Plex Mono with tabular figures, regardless of where it appears.
- **Do** signal state changes (pressed, active, focus) with a one-step tonal shift or a color wash, never a shadow.
- **Do** keep new components to the two-radius system (`10px` containers, `6px` controls) plus the `100px` pill for chip-shaped elements.
- **Do** respect safe-area insets on any fixed-position chrome (header, nav) — this ships as an installed PWA.
- **Do** let a recommendation card render nothing rather than a weak one — a "Combinada recomendada" section that only appears when there's a real one is more trustworthy than one that always shows something.

### Don't:
- **Don't** introduce a shadow, glow, or lift effect anywhere — depth is tonal, not elevated, by explicit system rule.
- **Don't** use gold decoratively (brand flourishes, non-value emphasis) — its rarity is what makes it legible as a signal.
- **Don't** use oxide and gold on the same figure, or use either where no verdict exists yet.
- **Don't** put a data value in Archivo — numbers that need to be compared or trusted belong in the mono/tabular type.
- **Don't** add a desktop breakpoint or wider layout without a real decision to expand beyond mobile-only; there's no existing desktop grammar to extend.
