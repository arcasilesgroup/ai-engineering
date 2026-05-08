# The 6-Layer Pipeline

Six layers (do not skip — one tool does not do everything): Capture → Organization → Deterministic Cuts → Programmable Composition (optional) → Generated Assets → Final Polish (human).

## Layer 1 — Capture

Collect the source material:

- **Screen Studio**: polished screen recordings for app demos, coding sessions
- **Raw camera footage**: vlog footage, interviews, event recordings
- **Desktop capture**: session recording with real-time context

Output: raw files ready for organization.

## Layer 2 — Organization

Use Claude to:

- **Transcribe and label**: generate transcript, identify topics and themes
- **Plan structure**: decide what stays, what gets cut, what order works
- **Identify dead sections**: find pauses, tangents, repeated takes
- **Generate edit decision list**: timestamps for cuts, segments to keep
- **Scaffold FFmpeg commands**: generate the cut commands and concat lists

This layer is about structure, not final creative taste.

## Layer 3 — Deterministic Cuts (FFmpeg)

FFmpeg handles the boring but critical work — extract by timestamp, batch cut from an edit decision list, concatenate segments, normalize audio, generate proxies. See the SKILL.md reference list for the recipe sheet.

## Layer 4 — Programmable Composition (Remotion) [Optional]

Use Remotion for overlays (text, branding, lower thirds), data visualizations, motion graphics, and reusable scene templates. Requires Node.js. `npx remotion render src/index.ts VlogComposition output.mp4`. Skip when programmable compositions are not needed.

## Layer 5 — Generated Assets

Cross-reference `ai-media` for voiceover (ElevenLabs/CSM-1B), music/SFX (fal.ai ThinkSound, VideoDB), insert shots/b-roll (fal.ai image models). Generate only what is missing.

## Layer 6 — Final Polish (Human Layer)

Traditional editor for pacing, caption cleanup, color grading, final audio mix, platform-specific export. AI clears repetitive work; humans make the final calls.

## Tool-Per-Job Table

| Tool              | Strength                                                     | Weakness                         |
| ----------------- | ------------------------------------------------------------ | -------------------------------- |
| Claude            | Organization, planning, code generation                      | Not the creative taste layer     |
| FFmpeg            | Deterministic cuts, batch processing, format conversion      | No visual editing UI             |
| Remotion          | Programmable overlays, composable scenes, reusable templates | Learning curve, requires Node.js |
| Screen Studio     | Polished screen recordings immediately                       | Only screen capture              |
| ElevenLabs        | Voice, narration, music, SFX                                 | Not the center of the workflow   |
| Descript / CapCut | Final pacing, captions, polish                               | Manual, not automatable          |
