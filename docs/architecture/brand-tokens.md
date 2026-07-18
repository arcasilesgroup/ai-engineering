# Brand Tokens

Single source for every visual asset (SVG infographics, fal art prompts, Mermaid
renders, diagrams). Values lifted verbatim from `.github/assets/banner-dark.svg`
and `.ai-engineering/reference/brand-voice.md`. Authority for prose: `brand-voice.md`.

## Palette

| Token | Hex | Use |
|-------|-----|-----|
| `bg-deep` | `#0B1120` | Background outer (radial stop 100%) |
| `bg-mid` | `#162844` | Background inner (radial stop 0%) |
| `accent` | `#00D4AA` | Teal accent — brackets, separators, glow, edges |
| `text` | `#F8FAFB` | Primary text / nodes |
| `grid` | `#FFFFFF` @ 4% | Faint grid lines |
| `bracket` | `#00D4AA` @ 30% | Corner brackets |
| `glow` | `#00D4AA` @ 8% | Radial glow behind focal element |

## Type

- Family: `'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', 'Consolas', monospace`.
- Wordmark: `{ai} engineering` — `{` and `}` in `accent`, `ai` + `engineering` in `text`, weight 700.

## Status grammar (no emoji)

`[PASS]` · `[WARN]` · `[FAIL]` · `[PENDING]` — textual, never color-only, never decorative symbols.

## Stat line

Mid-dot inventory: `53 skills · 9 agents · 6 surfaces · 1 governed flow`.

## Asset rules

- fal raster art = abstract branded illustration only; NO load-bearing text (labels live in SVG/Mermaid).
- SVG infographics ship light + dark twins, embedded via `<picture>` with descriptive alt text.
- Mermaid blocks set NO `%%{init}%%` theme (GitHub auto-adapts); pre-rendered to committed SVG for off-GitHub surfaces.
- All README/PyPI image URLs are absolute `raw.githubusercontent.com/.../main/...`.
