# Corpus: ai-design

One gateway with four routes — shape, system-build, imagery, verify — for a web, mobile,
native or CLI experience. It produces tokens, components with every state, a mobile-first
implementation, and accessibility evidence measured off the rendered result.

## Routes here

- "design the settings screen" — the plain trigger, and `shape` decides whether it is a new surface, an extension or a redesign before anything is drawn.
- "build us a design system with tokens and components" — `system-build`: tokens, then components, then each component's empty, loading, error and too-long states.
- "make this page work on a phone" — mobile-first is the build order here, not a later pass.
- "check the contrast and the focus states on the rendered page" — `verify` measures the rendered thing rather than the CSS somebody wrote.
- "what states are we missing on this component" — the state list is part of the artefact, and its absence is what this skill exists to catch.
- "add a motion spec to this transition so it feels intentional" — the motion detail routes to `/ai-review`'s motion lens, and the design that carries it is shaped here.

## Refuses

- "is this diff good enough to merge" — use `/ai-review`, because merge-ready judgement is a separate pass and this skill's own "No hace" says it does not own it.
- "write down that we chose this framework and why" — use `/ai-spec`, because no design document substitutes for a spec, an MADR or the Solution Intent.
- "the page is blank in Safari, find out why" — use `/ai-debug`, because that is a cause at `file:line` and not a design question.
- "implement task 4 of the plan" — use `/ai-build`, because executing an approved plan with a red test first is its job.
- "generate the hero image, we need one" — refused as an assumption: imagery is opt-in, and when it is used it carries an asset card with provider, model, prompt digest, sources and licence.
- "just make it look nicer" — refused as a trigger with nothing in it: this skill needs an audience, a surface and a spec, and "nicer" names none of the three.
- "axe passed, so we are accessible" — refused: a scanner is a filter, not a verdict, and AA is a floor somebody has to evidence line by line.
- "open the pull request with the new design" — use `/ai-ship`, because the changelog, the pull request and the closing keyword belong to it.
