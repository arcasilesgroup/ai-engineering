---
name: ai-media
description: "Generates images, videos, and audio via AI models (fal-ai MCP): cheap iteration models, expensive production finals, cost-estimate before generation. Trigger for 'generate an image', 'create a thumbnail', 'make a voiceover', 'AI video', 'text to speech for'. Not for design composition; use /ai-visual instead. Not for animation specs; use /ai-animation instead."
effort: mid
argument-hint: "image|video|audio [description]"
tags: [media, generation, fal-ai]
requires: { mcp: ["fal-ai"] }
---

# Media

Generate images, videos, and audio via fal.ai models over MCP with progressive quality — iterate cheap, finalize expensive. Modes: `image` (text-to-image + editing), `video` (text/image-to-video), `audio` (speech, music, SFX, video-to-audio).

## Workflow

Applies §10.2 YAGNI (don't pay for production models until composition is locked) and §10.1 KISS (simplest model that meets the need).

1. **Gate: MCP** — verify the fal.ai MCP server is configured. If missing, give setup instructions (key at [fal.ai](https://fal.ai)):

```json
"fal-ai": {
  "command": "npx",
  "args": ["-y", "fal-ai-mcp-server"],
  "env": { "FAL_KEY": "YOUR_FAL_KEY_HERE" }
}
```

2. **Estimate cost** before generating; report the estimate for expensive runs (video especially): `estimate_cost(model_name: "fal-ai/...", input: {...})`.
3. **Gate: ElevenLabs** — for TTS via ElevenLabs, verify `ELEVENLABS_API_KEY`; else fall back to `csm-1b` or inform the user.
4. **Generate progressively** — cheap model for prompt iteration, lock with `seed`, then switch to the production model for finals.
5. **Deliver** — file path/URL, model + parameters, cost incurred, iteration suggestions if quality is low.

Progression: nano-banana-2 -> nano-banana-pro · seedance-1-0-pro -> veo-3 · csm-1b -> ElevenLabs.

## Model Reference

| Model                       | Type  | Best For                                        | Cost Tier |
| --------------------------- | ----- | ----------------------------------------------- | --------- |
| `fal-ai/nano-banana-2`      | Image | Quick iterations, drafts, image editing         | Low       |
| `fal-ai/nano-banana-pro`    | Image | Production images, realism, typography          | Medium    |
| `fal-ai/seedance-1-0-pro`   | Video | Text-to-video, image-to-video, high motion      | High      |
| `fal-ai/kling-video/v3/pro` | Video | Text/image-to-video with native audio           | High      |
| `fal-ai/veo-3`              | Video | Video with generated sound, high visual quality | High      |
| `fal-ai/csm-1b`             | Audio | Conversational text-to-speech                   | Low       |
| `fal-ai/thinksound`         | Audio | Video-to-audio (matching sounds from video)     | Medium    |

- **Image params**: `prompt` (required); `image_size` (`square`, `portrait_4_3`, `landscape_16_9`, `portrait_16_9`, `landscape_4_3`); `num_images` (1-4); `seed`; `guidance_scale` (1-20, higher = more literal).
- **Video params**: `prompt` (required); `duration` (`"5s"`, `"10s"`); `aspect_ratio` (`"16:9"`, `"9:16"`, `"1:1"`); `seed`; `image_url` (source for image-to-video).
- **MCP tools**: `search`, `find`, `generate`, `result`, `status`, `cancel`, `estimate_cost`, `models`, `upload`.

## Image Editing

Nano Banana 2 with an input image for inpainting, outpainting, or style transfer:

```
upload(file_path: "/path/to/image.png")
generate(model_name: "fal-ai/nano-banana-2", input: {
  "prompt": "same scene but in watercolor style",
  "image_url": "<uploaded_url>",
  "image_size": "landscape_16_9"
})
```

For non-MCP integrations (ElevenLabs, VideoDB), follow `handlers/external-apis.md`.

## Common Mistakes

Using pure text-to-video when image-to-video would be more controllable; assuming fal.ai access covers ElevenLabs credentials (separate key).

## Integration

- **Called by**: user directly, `/ai-build`, `ai-video-editing` (Layer 5 generated assets)
- **Calls**: fal.ai MCP, ElevenLabs API, VideoDB API
- **See also**: `/ai-visual` (composed visuals), `/ai-slides` (deck visuals), `/ai-animation`

## Examples

```
/ai-media image hero for parallel agent planning blog
```

Iterates with `nano-banana-2` (cheap), locks composition with `seed`, switches to `nano-banana-pro` for the production final, returns URL + cost.

$ARGUMENTS
