# Social Media Reframing

## Aspect ratios

| Platform       | Aspect Ratio | Resolution          |
| -------------- | ------------ | ------------------- |
| YouTube        | 16:9         | 1920x1080           |
| TikTok / Reels | 9:16         | 1080x1920           |
| Instagram Feed | 1:1          | 1080x1080           |
| X / Twitter    | 16:9 or 1:1  | 1280x720 or 720x720 |

## Reframe with FFmpeg

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
