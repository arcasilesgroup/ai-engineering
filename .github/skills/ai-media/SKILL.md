---
name: ai-media
description: Use when generating images (thumbnails, hero images), videos (demos, b-roll, social clips), or audio (voiceover, music, SFX) using AI models. Requires fal-ai MCP server. Estimates cost before generation. Uses cheap models for iteration, production models for finals. Trigger for 'generate an image', 'create a thumbnail', 'make a voiceover', 'AI video'.
effort: medium
argument-hint: "image|video|audio [description]"
mode: agent
tags: [media, generation, fal-ai]
requires:
  mcp:
  - fal-ai
---



# Media

## Purpose

Generate images, videos, and audio using fal.ai models via MCP. Progressive quality pattern: iterate cheap, finalize expensive. Covers text-to-image, text/image-to-video, text-to-speech, and video-to-audio.

## When to Use

- `image`: generating images from text prompts (thumbnails, hero images, insert shots)
- `video`: creating videos from text or images (demos, b-roll, social clips)
- `audio`: generating speech, music, or sound effects (voiceover, background music, SFX)

## Process

### Step 1 -- Gate Check (MCP Required)

Verify the fal.ai MCP server is configured. If not available, inform the user and provide setup instructions:

```json
"fal-ai": {
  "command": "npx",
  "args": ["-y", "fal-ai-mcp-server"],
  "env": { "FAL_KEY": "YOUR_FAL_KEY_HERE" }
}
```

Get an API key at [fal.ai](https://fal.ai).

### Step 2 -- Estimate Cost

Before generating, always check estimated cost:
```
estimate_cost(model_name: "fal-ai/...", input: {...})
```

Inform the user of the estimate before proceeding with expensive generations (video especially).

### Step 3 -- ElevenLabs Gate Check

Before using ElevenLabs, verify `ELEVENLABS_API_KEY` is set. If not, fall back to csm-1b or inform the user.

### Step 4 -- Generate with Progressive Quality

Start with cheaper models for prompt iteration, then switch to production models for finals.

### Step 5 -- Deliver

Provide the generated media with:
- file path or URL
- model used and parameters
- cost incurred
- suggestions for iteration if quality is not satisfactory

## Quick Reference

### Model Table

| Model | Type | Best For | Cost Tier |
|-------|------|----------|-----------|
| `fal-ai/nano-banana-2` | Image | Quick iterations, drafts, image editing | Low |
| `fal-ai/nano-banana-pro` | Image | Production images, realism, typography | Medium |
| `fal-ai/seedance-1-0-pro` | Video | Text-to-video, image-to-video, high motion | High |
| `fal-ai/kling-video/v3/pro` | Video | Text/image-to-video with native audio | High |
| `fal-ai/veo-3` | Video | Video with generated sound, high visual quality | High |
| `fal-ai/csm-1b` | Audio | Conversational text-to-speech | Low |
| `fal-ai/thinksound` | Audio | Video-to-audio (matching sounds from video) | Medium |

### Image Parameters

| Param | Type | Options | Notes |
|-------|------|---------|-------|
| `prompt` | string | required | Describe what you want |
| `image_size` | string | `square`, `portrait_4_3`, `landscape_16_9`, `portrait_16_9`, `landscape_4_3` | Aspect ratio |
| `num_images` | number | 1-4 | How many to generate |
| `seed` | number | any integer | Reproducibility |
| `guidance_scale` | number | 1-20 | How closely to follow the prompt (higher = more literal) |

### Video Parameters

| Param | Type | Options | Notes |
|-------|------|---------|-------|
| `prompt` | string | required | Describe the video |
| `duration` | string | `"5s"`, `"10s"` | Video length |
| `aspect_ratio` | string | `"16:9"`, `"9:16"`, `"1:1"` | Frame ratio |
| `seed` | number | any integer | Reproducibility |
| `image_url` | string | URL | Source image for image-to-video |

### MCP Tools Available

| Tool | Purpose |
|------|---------|
| `search` | Find available models by keyword |
| `find` | Get model details and parameters |
| `generate` | Run a model with parameters |
| `result` | Check async generation status |
| `status` | Check job status |
| `cancel` | Cancel a running job |
| `estimate_cost` | Estimate generation cost |
| `models` | List popular models |
| `upload` | Upload files for use as inputs |

## Progressive Quality Pattern

Iteration (low-cost) -> Production (high-cost): nano-banana-2 -> nano-banana-pro · seedance-1-0-pro -> veo-3 · csm-1b -> ElevenLabs. Use `seed` for reproducible results when iterating; lock once composition works, then switch to the production model.

## Image Editing

Use Nano Banana 2 with an input image for inpainting, outpainting, or style transfer:
```
upload(file_path: "/path/to/image.png")
generate(model_name: "fal-ai/nano-banana-2", input: {
  "prompt": "same scene but in watercolor style",
  "image_url": "<uploaded_url>",
  "image_size": "landscape_16_9"
})
```

For non-MCP integrations (ElevenLabs, VideoDB), follow `handlers/external-apis.md`.

## Integration

- **Called by**: user directly, `/ai-dispatch`, `ai-video-editing` (Layer 5 generated assets)
- **Calls**: fal.ai MCP tools, ElevenLabs API, VideoDB API
- **Related**: `ai-slides` (generated visuals for presentations), `ai-video-editing` (asset generation for video pipeline)

## Common Mistakes

- Running expensive video generations without checking `estimate_cost` first
- Using production models (nano-banana-pro, veo-3) for initial prompt iteration
- Not using `seed` for reproducibility when iterating
- Pure text-to-video when image-to-video would give more controlled results
- Generating media without confirming MCP availability first
- Forgetting that ElevenLabs requires a separate API key (not fal.ai)

$ARGUMENTS
