---
name: ai-video-editing
description: "Edits real video footage: cuts recordings into highlights, transcribes and structures raw footage, runs FFmpeg operations (trim, concat, reframe, normalize audio), creates Remotion overlays, prepares social-platform cuts. Trigger for 'cut this video', 'edit the recording', 'make a highlight reel', 'reframe for TikTok', 'transcribe this footage'. Not for generating videos from prompts; use /ai-media instead. Not for animation specs; use /ai-animation instead."
effort: mid
argument-hint: "plan|organize|cut|compose [source]"
tags: [video, editing, ffmpeg]
requires: { bins: ["ffmpeg"], anyBins: ["npx"] }
---

# Video Editing

AI-assisted editing for real footage — not generation from prompts. Core thesis: the value is not generation, it is compression.

## Workflow

Applies §10.1 KISS (deterministic FFmpeg cuts over reinvented pipelines) and §10.2 YAGNI (compress real footage; generate assets only where footage is missing).

0. Load contexts: read `.ai-engineering/manifest.yml` `providers.stacks`; load `.ai-engineering/overrides/<stack>/conventions.md` per stack + `.ai-engineering/overrides/_shared/conventions.md`; load `.ai-engineering/team/*.md`.
1. **Gate** — verify `ffmpeg` (`ffmpeg -version`); install via `brew install ffmpeg` / `apt install ffmpeg` / `choco install ffmpeg`.
2. **Pick mode** — `plan` (design the edit structure from raw footage/transcript), `organize` (transcribe, label, identify segments, generate edit decision lists/EDL), `cut` (deterministic FFmpeg trim/split/concat/reframe/normalize), `compose` (programmable Remotion overlays + compositions, optional).
3. **Run the 6-layer pipeline** — Capture → Organization → Deterministic Cuts → Programmable Composition → Generated Assets → Final Polish (human).
4. **Cross-reference** `ai-media` for Layer 5 generated assets (voiceover, music/SFX, b-roll).

Detail: [6-layer pipeline + tool table](references/six-layer-pipeline.md), [FFmpeg recipes: extract / batch-cut / concat / proxy / silence detect](references/ffmpeg-recipes.md), [social-platform reframing presets](references/social-presets.md).

## Common Mistakes

- Forcing one tool to span every layer.
- Ignoring proxy / audio-normalization hygiene.

## Integration

Called by: user directly, `/ai-build`. Calls: `ffmpeg` (deterministic cuts), Remotion (compositions), `/ai-media` (Layer 5 generated assets). See also: `/ai-media` (asset generation), `/ai-slides` (deck embeds), `/ai-visual` (cover art).

## Examples

User: "cut this 60-minute talk into a 90-second highlight reel"

```
/ai-video-editing plan recording.mp4
```

Plans cuts, transcribes, identifies highlight beats, runs FFmpeg trim+concat, normalizes audio, outputs the reel.

$ARGUMENTS
