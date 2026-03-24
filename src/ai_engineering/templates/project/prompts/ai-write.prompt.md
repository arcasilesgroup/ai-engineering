---
name: ai-write
description: "Use when writing technical content: documentation, changelogs, articles, pitches, sprint reviews, and presentation outlines. Handler-based with audience targeting."
effort: high
argument-hint: "docs|changelog|content <type>|content-engine|crosspost|market-research|investor-materials|--audience developer|manager|executive"
mode: agent
tags: [writing, documentation, changelog, content, communication]
---



# Technical Writing

Router skill for comprehensive technical writing. Dispatches to handler files based on content type. Always: clear structure, audience-appropriate, no fluff.

## When to Use

- Writing or updating documentation (README, API docs, guides).
- Generating changelogs from conventional commits.
- Creating pitch decks, sprint reviews, blog posts, architecture board presentations.
- NOT for code explanations -- use `/ai-explain`.
- NOT for code changes -- use `ai-build agent`.

## Routing

| Sub-command | Handler | Purpose |
|-------------|---------|---------|
| `docs` | `handlers/docs.md` | README, API docs, guides, wiki pages |
| `changelog` | `handlers/changelog.md` | Release notes from conventional commits |
| `content` | `handlers/content.md` | Articles, pitches, presentations, sprint reviews |
| `content-engine` | `handlers/content-engine.md` | Platform-native social content with repurposing cascade |
| `crosspost` | `handlers/crosspost.md` | Multi-platform content distribution and adaptation |
| `market-research` | `handlers/market-research.md` | Research-to-decision synthesis (diligence, competitive, sizing) |
| `investor-materials` | `handlers/investor-materials.md` | Pitch decks, one-pagers, financial models, applications |

Default (no sub-command): `docs`.

## Audience Targeting

| Audience | Tone | Detail Level | Jargon |
|----------|------|-------------|--------|
| `developer` | Technical, precise | Implementation details | Full technical vocabulary |
| `manager` | Results-oriented | Impact and timeline | Minimal, explained when used |
| `executive` | Strategic | Business value and risk | None |

Default: `developer`.

## Quick Reference

```
/ai-write docs                              # documentation (default)
/ai-write changelog                         # release notes from commits
/ai-write content pitch                     # elevator pitch
/ai-write content sprint-review             # sprint review summary
/ai-write content blog                      # blog post
/ai-write content presentation              # presentation outline
/ai-write content architecture-board        # architecture decision for review
/ai-write content solution-intent           # solution intent document
/ai-write content-engine                    # platform-native social content
/ai-write crosspost                         # multi-platform distribution
/ai-write market-research                   # research synthesis (diligence, competitive, sizing)
/ai-write investor-materials                # pitch deck, one-pager, financial model
/ai-write docs --audience manager           # manager-targeted docs
```

## Shared Rules

- Write what users can DO, not what you BUILT.
- Active voice. Present tense.
- No "basically", "simply", "just".
- Every section earns its place -- cut anything that does not serve the reader.
- Audience determines vocabulary, not quality.

## Integration

- Composes with `/ai-commit` documentation gate for auto-updates.
- Changelog mode follows Keep a Changelog format.
- Content mode adapts to audience tier.

## References

- `.ai-engineering/manifest.yml` -- governance documentation requirements.
$ARGUMENTS

---

# Handler: changelog

Generate changelogs and release notes from conventional commits.

## Process

1. **Identify scope** -- determine range:
   - Between tags: `git log v1.0.0..v2.0.0 --oneline`.
   - Since last release: `git log $(git describe --tags --abbrev=0)..HEAD --oneline`.
   - Time-based: `git log --since="2 weeks ago" --oneline`.

2. **Collect material** -- for each commit/PR: message, changed files, linked issues.

3. **Classify impact**:
   - User-visible: behavior change, new capability, bug fix.
   - Internal: refactoring, tests, CI (exclude from changelog).
   - Breaking: API change, feature removal (requires migration guide).
   - Security: vulnerability fix (include CVE, impact, affected versions).

4. **Map to categories** (Keep a Changelog):
   - **Added**: new capability users could not do before.
   - **Changed**: existing capability improved or different.
   - **Deprecated**: still works, include removal timeline.
   - **Removed**: previously available, now gone.
   - **Fixed**: was broken, now works.
   - **Security**: vulnerability fix with CVE reference.

5. **Transform language** -- user-facing, not technical:
   ```
   Bad:  "Refactored ReportExporter to support pagination"
   Good: "Reports now load 3x faster when filtering large datasets"
   ```
   Rules: start with "You can now..." / "Fixed an issue where...", present tense, no internal references.

6. **Format CHANGELOG.md** -- entries in `[Unreleased]` section. For releases: rename to `[X.Y.Z] - YYYY-MM-DD`, add comparison links.

7. **Quality check** -- reject: "various bug fixes", "updated dependencies" without impact, internal jargon, missing dates, buried breaking changes.

## Output

- CHANGELOG.md entries in Keep a Changelog format.
- Optional: GitHub Release Notes with highlights, upgrade guide, contributors.

---

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

---

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

## Output

- Structured content document in markdown.
- Adapted to specified audience tier.

---

# Handler: crosspost

Multi-platform content distribution. Adapts a single message for each platform's native format and audience expectations.

## Platform Specs

| Platform | Short Limit | Long Limit | Hashtags | Link Preview | Best Time (UTC) |
|----------|------------|------------|----------|-------------|----------------|
| X | 280 chars | 4000 chars (premium) | 0-1 | Yes (unfurls) | 13:00-16:00 |
| LinkedIn | 3000 chars | 3000 chars | 3-5 | Yes | 07:00-10:00 |
| Threads | 500 chars | 500 chars | 0 | No | 11:00-14:00 |
| Bluesky | 300 chars | 300 chars | 0 | Yes (card) | 14:00-17:00 |

Notes:
- X premium allows 4000 chars but most followers see 280-char posts in feed. Write for 280; expand only for threads.
- LinkedIn shows ~210 chars before "see more". First line is the hook.
- Threads does not support link previews natively. Put the link in a reply.
- Bluesky uses link cards. Attach the URL as a card, not inline text.

## Workflow

### Step 1: Identify Core Message

Reduce the content to one sentence. This is the invariant across all platforms.

```text
Example: "We reduced CI pipeline time from 45 minutes to 3 minutes by replacing Docker layer caching with Depot."
```

### Step 2: Draft Primary Platform First

Write for the platform where the core audience lives. This draft sets the tone.

### Step 3: Adapt for Each Secondary Platform

For each additional platform, transform -- do not copy-paste. Follow platform-specific rules:

- **X**: compress. One sharp take. No preamble.
- **LinkedIn**: expand with professional context. What did you learn? What should the reader try?
- **Threads**: conversational. Shorter than LinkedIn. No hashtags.
- **Bluesky**: concise like X but can be slightly more casual. Attach link as card.

### Step 4: Stagger Publishing

- Primary platform: publish immediately.
- Secondary platforms: stagger by 30-60 minutes each.
- Cross-link only where natural. Do not say "as I posted on X..."

## Adaptation Examples

### Product Launch

**Core message**: "We shipped real-time collaboration. Multiple users can edit the same document simultaneously."

**X (280 chars)**:
```
We just shipped real-time collaboration.

Multiple cursors. Live presence. Conflict resolution that actually works.

No more "hey are you in that doc?" messages.

Try it: [link]
```

**LinkedIn (professional context)**:
```
Real-time collaboration is now live in [Product].

The hardest part was not the technology (CRDTs are well-documented).
The hardest part was making it feel invisible.

Users should never think about sync. They should just work.

Three things we got right:
- Presence indicators that fade after 30s of inactivity
- Conflict resolution that picks the most recent keystroke, not the last sync
- Offline edits that merge cleanly when reconnecting

If you are building multiplayer features, I wrote up the technical decisions here: [link]

#collaboration #productengineering #crdt
```

**Threads (conversational)**:
```
shipped real-time collab today. multiple people editing the same doc, live cursors, the whole thing.

the unlock was making conflict resolution invisible. users should never see a merge dialog.
```

**Bluesky (concise + card)**:
```
Shipped real-time collaboration today. Multiple cursors, live presence, invisible conflict resolution.

The hardest part: making sync feel like it doesn't exist.
[link card]
```

### Technical Insight

**Core message**: "Moving health checks from liveness to readiness probes cut our false-positive pod restarts by 90%."

**X**:
```
PSA: if your Kubernetes liveness probe checks database connectivity, you're going to have cascading restarts during a DB blip.

Move dependency checks to readiness probes. Let liveness just confirm the process is alive.

We cut false restarts by 90%.
```

**LinkedIn**:
```
A one-line Kubernetes change cut our false-positive pod restarts by 90%.

We had liveness probes checking database connectivity. When the DB had a 5-second hiccup, Kubernetes restarted every pod simultaneously -- turning a minor blip into a full outage.

The fix: move dependency checks to readiness probes. Liveness only confirms the process is alive.

Readiness failure removes the pod from the service (stops traffic). Liveness failure kills the pod (restarts it). Very different consequences.

If your liveness probe does anything beyond "is this process running," audit it today.

#kubernetes #sre #reliability
```

## Rules

- **Never identical copy** across platforms. Each version must feel native to where it appears.
- **Preserve the core message** across all versions. Facts and claims must be consistent.
- **Respect each platform's culture**. LinkedIn is professional. X is direct. Threads is casual. Bluesky is early-adopter.
- **One CTA per platform**. Do not stack "follow me on X, subscribe to my newsletter, and check out my YouTube."
- **No meta-references**. Do not say "I also posted this on LinkedIn" or "thread incoming."

## Output

- One adapted draft per target platform.
- Each draft includes: platform, character count, scheduled publish time (relative offset).
- Consistency check: verify all versions agree on facts, numbers, and claims.

---

# Handler: docs

Documentation authoring for README, API docs, guides, wiki pages, and CONTRIBUTING files.

## Pre-conditions

1. Read `.ai-engineering/manifest.yml` — `documentation` section.
2. Check `documentation.auto_update` flags to determine what to update.

## Process

1. **Detect doc type** -- classify: tutorial, how-to, explanation, reference, ADR.
2. **Read existing** -- if updating, read current content to preserve structure and links.
3. **Gather context** -- read source code, config, `manifest.yml`, project metadata.
4. **Apply Divio structure**:
   - **Tutorial**: learning-oriented, step-by-step, concrete outcomes.
   - **How-to**: task-oriented, assumes knowledge, goal-focused.
   - **Explanation**: understanding-oriented, context and reasoning.
   - **Reference**: information-oriented, accurate and complete.
5. **Write content** -- audience-appropriate vocabulary, active voice, no fluff.
6. **Validate** -- verify internal links resolve, markdown structure is valid.

## Doc Types

### README
- Project name and one-line description.
- Quick start (3 steps max to "hello world").
- Installation, usage, configuration.
- Contributing, license.

### README Update Mode

Triggered when `manifest.yml` `documentation.auto_update.readme` is `true`.

1. Scan project recursively for ALL README*.md files (README.md, README_es.md, etc.)
   - **Exclude**: `.venv/`, `node_modules/`, `.git/`, `__pycache__/`, `.pytest_cache/`, `build/`, `dist/`
2. For EACH README found:
   a. Read the README in context of its directory (what does this directory contain?)
   b. Read sibling files to understand the module/package purpose
   c. Update the README to reflect current state of that directory
   d. Preserve existing structure and formatting; update content in-place
3. Report which READMEs were updated and which were unchanged

### API Docs
- Endpoint/function signature.
- Parameters with types and constraints.
- Response format with examples.
- Error codes and handling.

### Guides
- Prerequisites clearly stated.
- Numbered steps with expected outcomes.
- Troubleshooting section for common failures.

### ADR (Architecture Decision Record)
- Status, context, decision, consequences.
- Alternatives considered with tradeoffs.
- Date and participants.

## Output

- Markdown file(s) ready to commit.
- Validation report: link check, structure check.

---

# Handler: investor-materials

Fundraising collateral: pitch decks, one-pagers, financial models, and accelerator applications. All materials must tell a consistent story backed by the same numbers.

## Golden Rule: All Materials Must Agree

Every investor-facing document draws from a single source of truth. If a number appears in the deck, it must match the one-pager, the financial model, and the application.

### Source of Truth Fields

Maintain these values in one place. Update once, propagate everywhere.

| Field | Example | Where it appears |
|-------|---------|-----------------|
| Traction metrics | "$45K MRR, 120 customers, 15% MoM growth" | Deck slide 4, one-pager section 2, application Q: traction |
| Pricing | "Starter $49/mo, Pro $149/mo, Enterprise custom" | Deck slide 6, financial model revenue assumptions |
| Raise size | "Raising $2M seed on $10M post-money" | Deck slide 11, one-pager header, application Q: raise |
| Use of funds | "60% engineering, 20% GTM, 20% ops" | Deck slide 11, one-pager section 5, financial model expenses |
| Team bios | Name, role, relevant credential (1 line each) | Deck slide 10, one-pager section 4, application Q: team |
| Milestones | "Q3: launch v2, Q4: 500 customers, Q1+1: Series A" | Deck slide 12, financial model projections, application Q: plan |

Before generating any material, ask the user to confirm or provide these values.

## Asset Guidance

### Pitch Deck (12 Slides)

Investors spend an average of 3 minutes and 44 seconds on a deck. Every slide earns its place.

```text
Slide  1: Title (company name, one-line description, logo)
Slide  2: Problem (who has it, how painful, how they cope today)
Slide  3: Solution (what you built, how it solves the problem)
Slide  4: Traction (revenue, users, growth rate -- real numbers)
Slide  5: Market (TAM/SAM/SOM with sources, not fantasy numbers)
Slide  6: Business model (pricing, unit economics, LTV:CAC)
Slide  7: Product (screenshot or demo, not architecture diagram)
Slide  8: How it works (the "why us" -- tech moat, unique insight)
Slide  9: Competition (positioning matrix, not feature checklist)
Slide 10: Team (relevant experience only -- why THIS team wins)
Slide 11: The ask (raise amount, valuation, use of funds breakdown)
Slide 12: Closing (milestones to next round, contact info)
```

Rules:
- One message per slide. If you need two points, you need two slides.
- Numbers over narratives. "15% MoM for 8 months" beats "rapid growth."
- Competition slide: use 2x2 matrix with meaningful axes, not a feature grid where you check every box.
- Product slide shows the product. Not the architecture. Not the tech stack.

### One-Pager / Investment Memo

A single page (PDF or markdown) that an investor forwards to partners.

```text
Structure:
  Header:  Company name | Stage | Raising $X at $Y valuation
  Section 1: Problem & Solution (3-4 sentences)
  Section 2: Traction (key metrics with timeframe)
  Section 3: Market (TAM with source, target segment)
  Section 4: Team (founders with 1-line bios)
  Section 5: Use of Funds (3-4 line items with percentages)
  Section 6: Contact (email, calendly link)
```

Rules:
- Fits on one page when printed. No exceptions.
- Lead with traction if you have it. Lead with team if you are pre-revenue.
- No jargon the investor's partners would need to look up.

### Financial Model

Three-scenario projection (bear, base, bull) with sensitivity analysis.

```text
Structure:
  Tab 1: Assumptions (clearly labeled inputs, color-coded)
  Tab 2: Revenue model (cohort-based or bottoms-up)
  Tab 3: Expense model (headcount plan, COGS, opex)
  Tab 4: P&L summary (monthly for 12mo, quarterly for 24mo)
  Tab 5: Cash flow (burn rate, runway, fundraise timing)
  Tab 6: Sensitivity analysis (what-if on 3-4 key drivers)
```

Scenarios:
- **Bear**: 50% of base case growth, higher churn, slower hiring.
- **Base**: plan-of-record assumptions.
- **Bull**: 150% of base case growth, lower churn, faster expansion.

Sensitivity analysis: vary these drivers independently:
- Monthly growth rate (+/- 5 percentage points).
- Churn rate (+/- 2 percentage points).
- Average contract value (+/- 20%).
- Sales cycle length (+/- 30 days).

Rules:
- Color-code assumptions: blue = input, black = formula, green = linked from another tab.
- Revenue must reconcile: units * price * conversion = revenue. No magic cells.
- Headcount must match use-of-funds slide.
- Include a runway calculation: "At base case burn, runway is X months without additional funding."

### Accelerator Applications

Common questions mapped to source of truth fields.

| Common Question | Source |
|----------------|--------|
| "Describe your company in one sentence" | Deck slide 1 subtitle |
| "What problem do you solve?" | Deck slides 2-3 |
| "What is your traction?" | Traction metrics |
| "How do you make money?" | Pricing + business model |
| "How big is the market?" | Market sizing (TAM/SAM/SOM) |
| "Who is on the team?" | Team bios |
| "How much are you raising?" | Raise size |
| "What will you do with the money?" | Use of funds |
| "What are your milestones for the next 12 months?" | Milestones |
| "Why now?" | Problem slide + market timing argument |

Rules:
- Answer the question asked. Do not dump your pitch into every text box.
- Keep answers concise. If the limit is 200 words, use 150.
- Match tone to the accelerator's brand (YC values directness; others may prefer polish).
- Use the same numbers as the deck. Reviewers cross-reference.

## Red Flags to Avoid

Investors pattern-match on these. Any one can sink a deal.

- **Unverifiable claims**: "We are the only company doing X" (you are probably not). Replace with specific differentiation.
- **Fuzzy market sizing**: "$100B TAM" with no methodology. Always show your math. Top-down AND bottom-up.
- **Inconsistent team roles**: CTO in the deck, "Technical Lead" in the application. Pick one title per person and use it everywhere.
- **Revenue math that does not sum**: if you claim 120 customers at $49/mo, your MRR better be close to $5,880, not "$45K MRR." Investors will check.
- **Vanity metrics without context**: "10,000 sign-ups" means nothing without activation rate, retention, or revenue.
- **Missing competitive response**: "No real competitors" is a red flag. Either you have not looked, or the market does not exist.
- **Vague use of funds**: "product development" is not specific. "Hire 3 engineers to build real-time collaboration (Q2-Q3)" is.
- **Milestone-free plans**: "scale the business" is not a milestone. "Reach $100K MRR by Q4" is.

## Output

- Requested asset(s) in markdown format, ready for design handoff.
- Consistency check: verify all numbers agree across generated materials.
- Red flag audit: flag any claims or numbers that could trigger investor scrutiny.

---

# Handler: market-research

Research synthesis that moves from raw information to defensible decisions. Structured for investors, operators, and strategists.

## Modes

Select the mode that matches the research question. If unclear, ask the user.

### 1. Investor/Fund Diligence

Evaluate a company, fund, or opportunity for investment decision-making.

**Scope**:
- Business model viability and unit economics.
- Market position and competitive dynamics.
- Team assessment (founder-market fit, key person risk).
- Financial health (burn rate, runway, revenue trajectory).
- Risk factors (regulatory, technical, market timing).

**Key questions to answer**:
- What is the company's unfair advantage?
- Is the business model sustainable at scale?
- What are the top 3 risks to the investment thesis?
- What would need to be true for this to return 10x?

### 2. Competitive Analysis

Map the competitive landscape for strategic positioning.

**Scope**:
- Direct and indirect competitors (identify 5-10).
- Feature comparison matrix across key dimensions.
- Pricing and packaging comparison.
- Go-to-market strategy differences.
- Strengths, weaknesses, and gaps for each player.

**Key questions to answer**:
- Where is the white space in the market?
- What do customers complain about with existing solutions?
- Which competitor is best positioned and why?
- What would a new entrant need to win?

### 3. Market Sizing

Estimate addressable market using both top-down and bottom-up methods.

**Top-down (TAM/SAM/SOM)**:
```text
TAM (Total Addressable Market)
  = Total market revenue if 100% adoption
  Source: industry reports, analyst estimates

SAM (Serviceable Addressable Market)
  = TAM filtered by geography, segment, and product fit
  Source: TAM * segment percentage

SOM (Serviceable Obtainable Market)
  = SAM filtered by realistic capture rate
  Source: SAM * estimated market share (typically 1-5% for entrants)
```

**Bottom-up**:
```text
SOM = (target customers) * (annual contract value) * (conversion rate)

Example:
  50,000 target companies in segment
  * $12,000 ACV
  * 2% conversion in year 1
  = $12M year-1 revenue
```

Rules:
- Always present both methods. If they diverge by >3x, explain why.
- State assumptions explicitly. Every number must trace to a source or assumption.
- Use conservative estimates for SOM. Aggressive projections erode credibility.

### 4. Technology/Vendor Research

Evaluate technology choices or vendor selection for build-vs-buy decisions.

**Scope**:
- Requirements mapping (must-have, nice-to-have, out-of-scope).
- Vendor comparison across: capability, pricing, support, lock-in risk.
- Total cost of ownership over 3-year horizon (license, integration, migration, support).
- Community and ecosystem health (GitHub stars are vanity; contributor count and release cadence matter).

**Key questions to answer**:
- What is the switching cost if this vendor fails or pivots?
- Does this technology solve the problem or just shift it?
- What is the team's ramp-up time?
- What do teams who left this technology migrate to, and why?

## Output Format

Every research deliverable follows this structure:

```text
1. Executive Summary (3-5 sentences, the decision in plain language)
2. Key Findings (5-7 bullet points, each with supporting evidence)
3. Implications (what this means for the decision at hand)
4. Risks and Caveats (what could invalidate these findings)
5. Recommendation (clear position with confidence level: high/medium/low)
6. Sources (numbered list, every claim traced to a source)
```

## Standards

- **Every claim sourced**. No unsourced assertions. If a data point comes from an assumption, label it as such.
- **Data older than 18 months flagged**. Prefix with "[DATA: YYYY]" so the reader knows the vintage.
- **Contrarian evidence included**. For every key finding, include at least one data point or argument that challenges it. Label as "Counter-evidence" or "Alternative view."
- **Confidence levels stated**. Rate each key finding as high/medium/low confidence based on source quality and corroboration.
- **No weasel words**. Replace "some analysts believe" with "Gartner's 2025 report estimates" or "based on 3 customer interviews." If the source is weak, say so directly.
- **Separate facts from interpretation**. Present data first, then state what you conclude from it. Do not blend them.

## Anti-patterns

- Market sizing with only top-down estimates and no bottom-up validation.
- Competitive analysis that only lists features without analyzing strategic implications.
- Diligence reports that omit risk factors or present only the bull case.
- Vendor research that compares marketing claims instead of documented capabilities.
- Using a single source for a critical claim.

## Output

- Structured research document in the output format above.
- All sources numbered and traceable.
- Confidence level stated for the overall recommendation.
