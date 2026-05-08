---
name: ai-video-editing
description: "Edits real video footage: cuts recordings into highlights, transcribes and structures raw footage, runs FFmpeg operations (trim, concat, reframe, normalize audio), creates Remotion overlays, prepares social-platform cuts. Trigger for 'cut this video', 'edit the recording', 'make a highlight reel', 'reframe for TikTok', 'transcribe this footage'. Not for generating videos from prompts; use /ai-media instead. Not for animation specs; use /ai-animation instead."
effort: high
argument-hint: "plan|organize|cut|compose [source]"
mode: agent
tags: [video, editing, ffmpeg]
requires:
  anyBins:
  - npx
  bins:
  - ffmpeg
mirror_family: copilot-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-video-editing/SKILL.md
edit_policy: generated-do-not-edit
---


# Video Editing

## Quick start

```
/ai-video-editing plan recording.mp4               # plan structure from raw footage
/ai-video-editing organize raw.mp4                 # transcribe + edit decision list
/ai-video-editing cut --edl cuts.txt               # deterministic FFmpeg cuts
/ai-video-editing compose --source demo.mp4 --aspect 9:16
```

## Workflow

AI-assisted editing for real footage. Not generation from prompts. Core thesis: **the value is not generation. The value is compression.**

1. **Gate check** — verify `ffmpeg` is available (`ffmpeg -version`); install via `brew install ffmpeg` / `apt install ffmpeg` / `choco install ffmpeg`.
2. **Pick mode** — `plan` (structure), `organize` (transcribe + EDL), `cut` (FFmpeg deterministic), `compose` (Remotion overlays, optional).
3. **Run the 6-layer pipeline** — Capture → Organization → Deterministic Cuts → Programmable Composition → Generated Assets → Final Polish (human).
4. **Cross-reference** `ai-media` for Layer 5 generated assets (voiceover, music/SFX, b-roll).

> Detail: see [the 6-layer pipeline + tool table](references/six-layer-pipeline.md), [FFmpeg recipes (extract / batch-cut / concat / proxy / silence detect)](references/ffmpeg-recipes.md), [social-platform reframing presets](references/social-presets.md).

## When to Use

- `plan`: designing the overall edit structure from raw footage or transcript
- `organize`: transcribing, labeling, identifying segments, generating edit decision lists
- `cut`: deterministic FFmpeg operations (trim, split, concatenate, reframe, normalize)
- `compose`: programmable overlays and compositions via Remotion (optional)

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

## Common Mistakes

- Trying to generate the whole video instead of compressing real footage.
- Skipping organization or final polish.
- Forcing one tool to span every layer.
- Ignoring proxy / audio-normalization hygiene.
- Replacing usable footage with generated assets.

## Examples

### Example 1 — highlight reel from a recording

User: "cut this 60-minute talk into a 90-second highlight reel"

```
/ai-video-editing plan recording.mp4
```

Plans cuts, transcribes, identifies highlight beats, runs FFmpeg trim+concat, normalizes audio, outputs the reel.

### Example 2 — reframe for TikTok

User: "reframe this 16:9 demo for TikTok 9:16"

```
/ai-video-editing compose --source demo.mp4 --aspect 9:16
```

Center-crop reframe with subject tracking via Remotion overlay, audio normalization, social-platform-ready output.

## Integration

Called by: user directly, `/ai-build`. Calls: `ffmpeg` (deterministic cuts), Remotion (compositions), `/ai-media` (Layer 5 generated assets). See also: `/ai-media` (asset generation), `/ai-slides` (deck embeds), `/ai-visual` (cover art).

$ARGUMENTS
