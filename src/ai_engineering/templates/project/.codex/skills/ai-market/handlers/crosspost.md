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

## API Integration

### Posting Execution Patterns

When the user requests actual posting (not just drafting), use the X API v2 handler for execution.

**Single post:**
```
1. Draft and confirm content with the user.
2. Delegate to handlers/x-api.md for X posting.
3. Use platform-native APIs or tools for LinkedIn, Threads, Bluesky.
4. Log post URLs and timestamps for the consistency check.
```

**Thread (X):**
```
1. Split content into thread segments respecting 280-char boundaries.
2. Post the first tweet, capture the tweet ID.
3. Reply-chain subsequent tweets using in_reply_to_tweet_id.
4. Return the thread URL (first tweet URL).
```

**Media attachments:**
```
1. Upload media first (image, video, GIF) to get a media_id.
2. Attach media_id to the post payload.
3. Alt text is required for all images (accessibility).
```

**Stagger pattern:**
```
Platform 1 (primary):  T+0 minutes
Platform 2:            T+30 minutes
Platform 3:            T+60 minutes
Platform 4:            T+90 minutes
```

Log each published URL. After all platforms are posted, run the consistency check: verify all versions agree on facts, numbers, and claims.

## Output

- One adapted draft per target platform.
- Each draft includes: platform, character count, scheduled publish time (relative offset).
- Consistency check: verify all versions agree on facts, numbers, and claims.
