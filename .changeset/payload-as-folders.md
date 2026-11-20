---
"ai-engineering": patch
---

The binary now carries its skills, agents and templates as plain folders (`bun build --compile --asset`) and reads them by path, so the repository no longer commits a generated asset registry, text copies of skill scripts or the compiled chain bundle. The chain bundle the Oh My Pi, Pi and OpenCode plugins import is built fresh by every build, test run and npm pack. What gets installed is unchanged.
