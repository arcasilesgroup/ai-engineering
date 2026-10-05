# Narration script

The voice is generated locally with Kokoro, through HyperFrames:

```bash
pip install kokoro-onnx soundfile
npx hyperframes tts "<line>" -o audio/s1.wav --voice am_michael
```

The eight lines, one per scene. The scene timings in `index.html` come from the
duration of each clip plus a short pause.

1. **the problem** (10.13s) · Your coding agent can already run any command, edit any file, and read any page. The problem is what stands between the request and the action: nothing.
2. **what it is** (11.16s) · ai-eng is a guardrail layer that sits under the agent you already use. It reads every tool call first, and answers allow, deny, or a rewritten command.
3. **install** (11.14s) · Install it once. Run ai-eng init inside your repository. It writes a contract the agent cannot execute before you approve it, and installs the git hooks.
4. **proof** (8.98s) · Then ask it how it is doing. ai-eng doctor fires a real adversarial payload through the chain, and proves the deny comes back.
5. **the guards** (10.97s) · Every call passes six guards in order: self-protect, no-verify, policy, injection, wrap, and loop. The first deny wins, and a receipt lands on disk.
6. **the loop** (17.71s) · It also installs thirty skills. One of them is the whole workflow: ai-orchestrator. It splits the feature into checkpoints you approve, builds each one through its gates, and stops for you twice. Everything else is optional, and it composes with whatever you already run.
7. **one workflow** (22.38s) · So a whole feature runs as one loop. You bring a fuzzy idea. ai-brainstorm pins it down. You approve the checkpoints. The orchestrator builds each one and runs it through its gates. A failed gate re-plans and tries again until it passes. When the app is done, you review it, and the recap shows the diff. Every gate is a receipt in git.
8. **close** (7.96s) · No model calls. No hosted state. Your key, your model. Install it, run doctor, and see the deny for yourself.

To swap in a human voice, replace `audio/sN.mp3` with a recording of the same
line, keep the file name, and re-render. Adjust `data-start` and `data-duration`
on the scene and its audio clip if a line runs longer.

```bash
npx hyperframes check    # lint + runtime + layout + contrast
npx hyperframes render   # writes renders/<name>.mp4
```
