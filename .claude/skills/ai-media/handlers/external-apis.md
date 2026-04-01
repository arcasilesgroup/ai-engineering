# Handler: External APIs (Non-MCP Integrations)

## Purpose

Direct API integration patterns for services not available through MCP. Use these when fal.ai MCP tools do not cover the required capability.

## ElevenLabs TTS (Direct API, No MCP)

For professional voice synthesis, use ElevenLabs directly:

```python
import os, requests

resp = requests.post(
    f"https://api.elevenlabs.io/v1/text-to-speech/<voice_id>",
    headers={
        "xi-api-key": os.environ["ELEVENLABS_API_KEY"],
        "Content-Type": "application/json"
    },
    json={
        "text": "Your text here",
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
)
with open("output.mp3", "wb") as f:
    f.write(resp.content)
```

## VideoDB Generative Audio

If VideoDB is configured:

```python
audio = coll.generate_voice(text="Your narration here", voice="alloy")
music = coll.generate_music(prompt="upbeat electronic background music", duration=30)
sfx = coll.generate_sound_effect(prompt="thunder crack followed by rain")
```
