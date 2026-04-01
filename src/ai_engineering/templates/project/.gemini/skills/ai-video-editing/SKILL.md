---
name: ai-video-editing
description: "Use when editing real video footage: cutting recordings into highlights, transcribing and structuring raw footage, running FFmpeg operations (trim, concat, reframe, normalize audio), creating Remotion overlays, or preparing social platform cuts. Trigger for 'cut this video', 'edit the recording', 'make a highlight reel', 'reframe for TikTok'. Not for generating videos from prompts — use /ai-media."
effort: high
argument-hint: "plan|organize|cut|compose [source]"
tags: [video, editing, ffmpeg]
requires:
  anyBins:
  - npx
  bins:
  - ffmpeg
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

```
Layer 1: Capture (Screen Studio / raw footage)
Layer 2: Organization (Claude / transcript / edit plan)
Layer 3: Deterministic Cuts (FFmpeg)
Layer 4: Programmable Composition (Remotion) [optional]
Layer 5: Generated Assets (ai-media skill)
Layer 6: Final Polish (Descript / CapCut) [human]
```

Each layer has a specific job. Do not skip layers. Do not try to make one tool do everything.

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

**Create proxy for faster editing:**
```bash
ffmpeg -i raw.mp4 -vf "scale=960:-2" -c:v libx264 -preset ultrafast -crf 28 proxy.mp4
```

**Extract audio for transcription:**
```bash
ffmpeg -i raw.mp4 -vn -acodec pcm_s16le -ar 16000 audio.wav
```

**Normalize audio levels:**
```bash
ffmpeg -i segment.mp4 -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:v copy normalized.mp4
```

**Scene detection:**
```bash
ffmpeg -i input.mp4 -vf "select='gt(scene,0.3)',showinfo" -vsync vfr -f null - 2>&1 | grep showinfo
```

**Silence detection (find dead air):**
```bash
ffmpeg -i input.mp4 -af silencedetect=noise=-30dB:d=2 -f null - 2>&1 | grep silence
```

### Layer 4 -- Programmable Composition (Remotion) [Optional]

Remotion turns editing problems into composable code. Use it when you need:
- Overlays: text, images, branding, lower thirds
- Data visualizations: charts, stats, animated numbers
- Motion graphics: transitions, explainer animations
- Composable scenes: reusable templates across videos

```bash
npx remotion render src/index.ts VlogComposition output.mp4
```

Remotion requires Node.js. Skip this layer if the user does not need programmable compositions. See the [Remotion docs](https://www.remotion.dev/docs) (external reference -- may require manual verification) for API reference.

### Layer 5 -- Generated Assets

Generate only what you need. Do not generate the whole video.

Cross-reference the `ai-media` skill for:
- Voiceover (ElevenLabs or CSM-1B)
- Background music and SFX (fal.ai ThinkSound, VideoDB)
- Insert shots, thumbnails, or b-roll that does not exist (fal.ai image models)

### Layer 6 -- Final Polish (Human Layer)

The last layer is human. Use a traditional editor for:
- **Pacing**: adjust cuts that feel too fast or slow
- **Captions**: auto-generated, then manually cleaned
- **Color grading**: basic correction and mood
- **Final audio mix**: balance voice, music, and SFX levels
- **Export**: platform-specific formats and quality settings

This is where taste lives. AI clears the repetitive work. You make the final calls.

## Quick Reference

### Tool-Per-Job Table

| Tool | Strength | Weakness |
|------|----------|----------|
| Claude | Organization, planning, code generation | Not the creative taste layer |
| FFmpeg | Deterministic cuts, batch processing, format conversion | No visual editing UI |
| Remotion | Programmable overlays, composable scenes, reusable templates | Learning curve, requires Node.js |
| Screen Studio | Polished screen recordings immediately | Only screen capture |
| ElevenLabs | Voice, narration, music, SFX | Not the center of the workflow |
| Descript / CapCut | Final pacing, captions, polish | Manual, not automatable |

### Social Media Reframing

| Platform | Aspect Ratio | Resolution |
|----------|-------------|------------|
| YouTube | 16:9 | 1920x1080 |
| TikTok / Reels | 9:16 | 1080x1920 |
| Instagram Feed | 1:1 | 1080x1080 |
| X / Twitter | 16:9 or 1:1 | 1280x720 or 720x720 |

**Reframe with FFmpeg:**
```bash
# 16:9 to 9:16 (center crop)
ffmpeg -i input.mp4 -vf "crop=ih*9/16:ih,scale=1080:1920" vertical.mp4

# 16:9 to 1:1 (center crop)
ffmpeg -i input.mp4 -vf "crop=ih:ih,scale=1080:1080" square.mp4
```

## Key Principles

1. **Edit, don't generate.** This workflow is for cutting real footage, not creating from prompts.
2. **Structure before style.** Get the story right in Layer 2 before touching anything visual.
3. **FFmpeg is the backbone.** Boring but critical. Where long footage becomes manageable.
4. **Remotion for repeatability.** If you will do it more than once, make it a Remotion component.
5. **Generate selectively.** Only use AI generation for assets that don't exist, not for everything.
6. **Taste is the last layer.** AI clears repetitive work. You make the final creative calls.

## Integration

- **Called by**: user directly, `/ai-dispatch`
- **Calls**: FFmpeg (deterministic cuts), Remotion (optional compositions), `ai-media` (Layer 5 generated assets)
- **Related**: `ai-slides` (presentations from video content), `ai-media` (asset generation)

## Common Mistakes

- Trying to generate the whole video instead of editing real footage
- Skipping Layer 2 (organization) and jumping straight to cuts
- Making one tool do everything instead of respecting layer boundaries
- Using AI generation for assets that already exist as footage
- Forgetting to normalize audio levels before final assembly
- Not creating proxies for large files (FFmpeg editing on 4K originals is slow)
- Skipping the human polish layer -- AI handles structure, humans handle taste

$ARGUMENTS
