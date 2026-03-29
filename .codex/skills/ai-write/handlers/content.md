# Handler: content

Technical content creation: pitches, sprint reviews, presentations, blog posts, architecture boards, and solution intent documents.

## Content Types

### pitch
Elevator pitch for a feature, project, or initiative.
1. **Problem** -- 1-2 sentences on the pain point.
2. **Solution** -- what you built and how it solves the problem.
3. **Impact** -- quantified results or expected outcomes.
4. **Ask** -- what you need (approval, resources, feedback).

### sprint-review
Sprint review summary for stakeholders.
1. **Completed** -- features delivered with demo-ready descriptions.
2. **Metrics** -- velocity, burndown, quality indicators.
3. **Blockers** -- what slowed the team and how it was resolved.
4. **Next sprint** -- planned work and risks.

### blog
Technical blog post for developer audience.
1. **Hook** -- open with the problem or surprising finding.
2. **Context** -- why this matters, who benefits.
3. **Solution** -- technical walkthrough with code examples.
4. **Results** -- measured outcomes, benchmarks.
5. **Conclusion** -- key takeaway and call to action.

### presentation
Presentation outline (slide-by-slide structure).
1. **Title slide** -- topic, author, date.
2. **Problem/context** -- why we are here (2-3 slides).
3. **Solution/demo** -- what we built (3-5 slides).
4. **Results/impact** -- what changed (2-3 slides).
5. **Next steps** -- what is needed (1 slide).
6. **Appendix** -- technical detail for Q&A.

### architecture-board
Architecture decision presentation for review board.
1. **Context** -- business driver and technical constraint.
2. **Options evaluated** -- comparison matrix with criteria.
3. **Recommendation** -- selected option with rationale.
4. **Risk assessment** -- what could go wrong and mitigation.
5. **Implementation plan** -- phases, timeline, rollback.

### solution-intent
Solution intent document (SAFe-style).
1. **Vision** -- desired end state.
2. **Current state** -- what exists today.
3. **Solution overview** -- architecture, components, boundaries.
4. **Compliance** -- regulatory and governance requirements.
5. **Economic framework** -- cost, benefit, ROI estimate.
6. **Key decisions** -- made and pending.

## Audience Adaptation

- **Developer**: include code snippets, technical tradeoffs, implementation detail.
- **Manager**: focus on timeline, resource needs, risk, progress metrics.
- **Executive**: focus on business value, strategic alignment, ROI, competitive advantage.

## Voice Capture

### Input Collection

Before writing in someone's voice, gather at least 3 of:
- Published articles or blog posts
- Newsletters or email campaigns
- Social media posts (X, LinkedIn, Threads)
- Internal docs, memos, or Slack messages
- An explicit style guide

### What to Extract

| Signal | What to Look For |
|--------|-----------------|
| Sentence rhythm | Short/long mix, fragments, run-ons, parentheticals |
| Register | Formal, conversational, sharp/provocative, academic |
| Rhetorical devices | Questions, analogies, lists, repetition, callbacks |
| Humor tolerance | None, dry, self-deprecating, absurdist |
| Formatting habits | Header frequency, bullet vs prose, code blocks, pull quotes |

### Default Fallback

When no voice references are provided, default to: **direct, operator-style voice**. Concrete, practical, low on hype. Lead with the thing, explain after. Prefer short sentences.

### Banned Patterns

Delete and rewrite any of these on sight:
- "In today's rapidly evolving landscape" (and all variants)
- "Moreover" / "Furthermore" / "Additionally" as paragraph openers
- "game-changer" / "cutting-edge" / "revolutionary" / "disruptive"
- Vague claims without evidence ("significantly improves", "greatly enhances")
- Bio or credibility claims not backed by provided context ("as a thought leader")

If a draft contains any banned pattern, it is not finished.

## Output

- Structured content document in markdown.
- Adapted to specified audience tier.
