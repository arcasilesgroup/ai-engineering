# Handler: content-engine

Platform-native social content creation. Transforms source material into audience-specific, platform-optimized content.

## Pre-flight Clarification

Before writing, gather these four inputs. If any are missing, ask the user.

1. **Source asset** -- what are we working from? (blog post, launch announcement, talk recording, product feature, data/report)
2. **Audience** -- who is this for? (developers, founders, investors, hiring managers, general tech)
3. **Platform** -- where does this publish? (X, LinkedIn, TikTok, YouTube, Newsletter, multiple)
4. **Goal** -- what should the reader do after? (click link, sign up, share, reply, change perception)

## Platform Guidance

### X (formerly Twitter)

- **Limit**: 280 characters (free), 4000 characters (premium). Write for 280 by default.
- **Hook**: first 70 characters determine if people stop scrolling.
- **Structure**: one idea per post. Thread for multi-point arguments.
- **Hashtags**: 0-1 max. No hashtag spam. They reduce engagement on X.
- **Threads**: first post is the hook, last post has the CTA. Each post must stand alone if quoted.
- **Avoid**: starting with "I", walls of text, obvious engagement bait ("what do you think?").

### LinkedIn

- **Limit**: 3000 characters. Sweet spot is 1200-1800.
- **Hook**: strong first line -- it shows before the "see more" fold. Make it specific and surprising.
- **Structure**: short paragraphs (1-2 sentences). White space is your friend. Use line breaks aggressively.
- **Hashtags**: 3-5 relevant hashtags at the end. Industry-specific over generic.
- **CTA**: ask a genuine question or invite a specific action.
- **Avoid**: humble brags disguised as lessons, "I'm humbled to announce", generic motivational content.

### TikTok

- **First 3 seconds**: viewer decides to stay or scroll. Open with the payoff, conflict, or bold claim.
- **Structure**: hook (3s) -> context (10s) -> value (20-40s) -> CTA (5s).
- **Text overlay**: use for key points, timestamps, or the unexpected twist.
- **Audio**: trending sounds boost discovery. Original audio builds authority.
- **Avoid**: long intros, "hey guys so today I wanted to talk about", slow builds.

### YouTube

- **Thumbnail + Title**: 90% of the click decision. Title is a promise, thumbnail is proof.
- **Hook**: first 30 seconds must deliver on the title's promise or create an open loop.
- **Chapters**: add timestamps. Viewers scan before committing.
- **Structure**: hook (30s) -> problem (2min) -> solution (core) -> results -> CTA.
- **Description**: front-load keywords in first 2 lines. Links and timestamps below.
- **Avoid**: "before we start, hit subscribe", long sponsor reads at the beginning.

### Newsletter

- **One lens**: each issue explores one topic deeply. Do not make it a link roundup unless that is the format.
- **Subject line**: specific > clever. "How we cut deploy time from 45min to 3min" beats "This week in DevOps".
- **Structure**: opening hook (why now) -> insight (the meat) -> implication (so what) -> one CTA.
- **Length**: 500-1500 words. Respect inbox time.
- **Avoid**: multiple CTAs, recap-style "in case you missed it" padding, generic sign-offs.

## Repurposing Cascade

Transform one anchor piece into platform-native content.

```text
Step 1: Identify anchor asset (blog post, talk, report, launch)
                    |
Step 2: Extract 3-7 atomic ideas
        (standalone insights that hold value without context)
                    |
Step 3: Draft platform-native version for each idea
        - X: compress to one sharp post (or thread if multi-step)
        - LinkedIn: expand with professional context and lesson learned
        - TikTok: identify the most visual/demo-able idea
        - Newsletter: weave 2-3 ideas into one narrative
                    |
Step 4: Sequence for publishing
        - Primary platform first (where the audience lives)
        - Secondary platforms staggered over 24-72 hours
```

Rules for atomic ideas:
- Each idea must be valuable without reading the anchor.
- Frame as insight, not summary. "We found X" not "The blog covers X".
- Different angles for different platforms -- same fact, different framing.

## Quality Gate

Before delivering content, verify:

- [ ] No generic hype language ("game-changer", "revolutionary", "excited to share").
- [ ] Hook is specific -- names a number, outcome, or tension. Not "here is what I learned".
- [ ] Platform constraints respected (character limits, structure norms).
- [ ] CTA matches the stated goal. One CTA per piece.
- [ ] Could a competitor post the same content? If yes, it is too generic. Add specifics.
- [ ] Read the first line in isolation. Does it earn the second line?

## Output

- Platform-native drafts ready to post.
- Each draft tagged with: platform, character count, target audience, goal.
- Repurposing map showing which atomic idea each draft derives from.
