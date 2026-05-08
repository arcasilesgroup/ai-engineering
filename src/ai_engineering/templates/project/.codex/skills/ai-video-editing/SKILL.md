---
name: ai-video-editing
description: "Edits real video footage: cuts recordings into highlights, transcribes and structures raw footage, runs FFmpeg operations (trim, concat, reframe, normalize audio), creates Remotion overlays, prepares social-platform cuts. Trigger for 'cut this video', 'edit the recording', 'make a highlight reel', 'reframe for TikTok', 'transcribe this footage'. Not for generating videos from prompts; use /ai-media instead. Not for animation specs; use /ai-animation instead."
effort: high
argument-hint: "plan|organize|cut|compose [source]"
tags: [video, editing, ffmpeg]
requires:
  anyBins:
  - npx
  bins:
  - ffmpeg
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-video-editing/SKILL.md
edit_policy: generated-do-not-edit
---


# Video Editing

## Purpose

AI-assisted editing for real footage. Not generation from prompts. The core thesis: AI video editing is useful when you stop asking it to create the whole video and start using it to compress, structure, and augment real footage. **The value is not generation. The value is compression.**

## When to Use

- `plan`: designing the overall edit structure from raw footage or transcript
- `organize`: transcribing, labeling, identifying segments, generating edit decision lists
- `cut`: deterministic FFmpeg operations (trim, split, concatenate, reframe, normalize)
- `compose`: programmable overlays and compositions via Remotion (optional)

## Process

### Gate Check -- FFmpeg Required

Verify `ffmpeg` is available: `ffmpeg -version`. If not installed, provide platform-specific install instructions (`brew install ffmpeg` / `apt install ffmpeg` / `choco install ffmpeg`).

### The 6-Layer Pipeline

Six layers (do not skip; one tool does not do everything): Capture → Organization → Deterministic Cuts → Programmable Composition (optional) → Generated Assets → Final Polish (human).

### Layer 1 -- Capture

Collect the source material:

- **Screen Studio**: polished screen recordings for app demos, coding sessions
- **Raw camera footage**: vlog footage, interviews, event recordings
- **Desktop capture**: session recording with real-time context

Output: raw files ready for organization.

### Layer 2 -- Organization

Use Claude to:

- **Transcribe and label**: generate transcript, identify topics and themes
- **Plan structure**: decide what stays, what gets cut, what order works
- **Identify dead sections**: find pauses, tangents, repeated takes
- **Generate edit decision list**: timestamps for cuts, segments to keep
- **Scaffold FFmpeg commands**: generate the cut commands and concat lists

This layer is about structure, not final creative taste.

### Layer 3 -- Deterministic Cuts (FFmpeg)

FFmpeg handles the boring but critical work.

**Extract segment by timestamp:**

```bash
ffmpeg -i raw.mp4 -ss 00:12:30 -to 00:15:45 -c copy segment_01.mp4
```

**Batch cut from edit decision list:**

```bash
while IFS=, read -r start end label; do
  ffmpeg -i raw.mp4 -ss "$start" -to "$end" -c copy "segments/${label}.mp4"
done < cuts.txt
```

**Concatenate segments:**

```bash
for f in segments/*.mp4; do echo "file '$f'"; done > concat.txt
ffmpeg -f concat -safe 0 -i concat.txt -c copy assembled.mp4
```

**Common FFmpeg recipes:**

```bash
# Proxy:    ffmpeg -i raw.mp4 -vf "scale=960:-2" -c:v libx264 -preset ultrafast -crf 28 proxy.mp4
# Audio:    ffmpeg -i raw.mp4 -vn -acodec pcm_s16le -ar 16000 audio.wav
# Normalize: ffmpeg -i seg.mp4 -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:v copy normalized.mp4
# Scene:    ffmpeg -i input.mp4 -vf "select='gt(scene,0.3)',showinfo" -vsync vfr -f null - 2>&1 | grep showinfo
# Silence:  ffmpeg -i input.mp4 -af silencedetect=noise=-30dB:d=2 -f null - 2>&1 | grep silence
```

### Layer 4 -- Programmable Composition (Remotion) [Optional]

Use Remotion for overlays (text, branding, lower thirds), data visualizations, motion graphics, and reusable scene templates. Requires Node.js. `npx remotion render src/index.ts VlogComposition output.mp4`. Skip when programmable compositions are not needed.

### Layer 5 -- Generated Assets

Cross-reference `ai-media` for voiceover (ElevenLabs/CSM-1B), music/SFX (fal.ai ThinkSound, VideoDB), insert shots/b-roll (fal.ai image models). Generate only what is missing.

### Layer 6 -- Final Polish (Human Layer)

Traditional editor for pacing, caption cleanup, color grading, final audio mix, platform-specific export. AI clears repetitive work; humans make the final calls.

## Quick Reference

### Tool-Per-Job Table

| Tool              | Strength                                                     | Weakness                         |
| ----------------- | ------------------------------------------------------------ | -------------------------------- |
| Claude            | Organization, planning, code generation                      | Not the creative taste layer     |
| FFmpeg            | Deterministic cuts, batch processing, format conversion      | No visual editing UI             |
| Remotion          | Programmable overlays, composable scenes, reusable templates | Learning curve, requires Node.js |
| Screen Studio     | Polished screen recordings immediately                       | Only screen capture              |
| ElevenLabs        | Voice, narration, music, SFX                                 | Not the center of the workflow   |
| Descript / CapCut | Final pacing, captions, polish                               | Manual, not automatable          |

### Social Media Reframing

| Platform       | Aspect Ratio | Resolution          |
| -------------- | ------------ | ------------------- |
| YouTube        | 16:9         | 1920x1080           |
| TikTok / Reels | 9:16         | 1080x1920           |
| Instagram Feed | 1:1          | 1080x1080           |
| X / Twitter    | 16:9 or 1:1  | 1280x720 or 720x720 |

**Reframe with FFmpeg:**

```bash
# 16:9 to 9:16 (center crop)
ffmpeg -i input.mp4 -vf "crop=ih*9/16:ih,scale=1080:1920" vertical.mp4

# 16:9 to 1:1 (center crop)
ffmpeg -i input.mp4 -vf "crop=ih:ih,scale=1080:1080" square.mp4
```

## Key Principles

1. **Remotion for repeatability.** If you will do it more than once, make it a Remotion component.
2. **Generate selectively.** Only use AI generation for assets that don't exist, not for everything.

## Common Mistakes

Do not try to generate the whole video, skip organization or polish, force one tool to do every layer, ignore proxy/audio normalization hygiene, or replace usable footage with generated assets.

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

Called by: user directly, `/ai-dispatch`. Calls: `ffmpeg` (deterministic cuts), Remotion (compositions), `/ai-media` (Layer 5 generated assets). See also: `/ai-media` (asset generation), `/ai-slides` (deck embeds), `/ai-canvas` (cover art).

$ARGUMENTS
