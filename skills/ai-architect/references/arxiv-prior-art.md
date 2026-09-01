# arXiv Prior-Art Deep Dive

Read this only when the **Prior-Art Deep Dive (arXiv)** gate in `SKILL.md` has already fired. The gate is the entry condition; this file is the loop.

Builders do not waste hours because they lack skill. They waste hours because they start building before checking whether the hard part has already been solved and published, with the failure modes already known. arXiv is the largest source of truth for "has anyone done this", and almost nobody about to write code reads it first. This loop makes the agent read it first.

Three phases. Fetching is not divergence. Find real documents, read each in isolation, then converge. Skipping the isolation step turns this into a model guessing about papers it has not actually read.

## Phase 0 - Categorize

Map the build problem onto 3-5 arXiv subject categories and 3-6 concrete search terms (the technical mechanism words: "cache invalidation", not "caching system"). Pick from the table below, or name another category id if you are confident of it.

| Category | Covers |
|---|---|
| cs.AI | general AI systems, agents, planning, knowledge representation |
| cs.LG | learning algorithms, training methods, model architectures |
| cs.CL | NLP, language models, text processing |
| cs.CV | image/video understanding, generation, perception |
| cs.IR | search, ranking, recommendation, retrieval-augmented systems |
| cs.DC | distributed systems, consensus, sharding, replication, scheduling |
| cs.DB | storage engines, query processing, indexing, transactions, consistency |
| cs.SE | development practices, testing, program analysis, tooling |
| cs.PL | language design, type systems, compilers, runtimes |
| cs.CR | protocols, authentication, adversarial robustness, privacy |
| cs.NI | routing, congestion control, edge/CDN |
| cs.OS | kernels, schedulers, memory management, virtualization |
| cs.HC | interface design, usability, interaction models |
| cs.MA | coordination, negotiation, emergent behavior among agents |
| cs.RO | control, perception, manipulation, motion planning |
| cs.DS | algorithmic techniques, complexity, data structure design |
| cs.GT | mechanism design, auctions, incentive-compatible systems |
| stat.ML | statistical learning theory, probabilistic models |
| eess.SP / eess.SY | signal processing / control theory |
| math.OC | optimization, scheduling, resource allocation |

If the problem is pure product or business framing with no obvious technical mechanism, say so plainly, but still commit to a best-effort technical angle. Most build problems have one (caching, consistency, ranking, scheduling, retrieval) even unphrased.

## Phase 1 - Fetch (real HTTP, no generation)

For each chosen category, call **WebFetch** against arXiv's real export API. Do not paraphrase this step from memory; actually fetch it:

    https://export.arxiv.org/api/query?search_query=cat:<CATEGORY>+AND+(all:"<term1>"+OR+all:"<term2>")&start=0&max_results=4&sortBy=relevance&sortOrder=descending

Ask WebFetch to return, per `<entry>`: the arXiv id, title, abstract, authors, published date, and the `abs`/`pdf` links, verbatim from the feed, not summarized. This is a real Atom XML feed. Treat every field as ground truth, and never invent a paper, id, or detail not present in the response.

If a category returns fewer than 2 results, retry that category's query with the search terms dropped (`cat:<CATEGORY>` alone). Do not pad the result set with irrelevant hits to reach a target count. If everything comes back thin, say so in the output rather than manufacturing findings.

**Courtesy:** arXiv asks for one request at a time with a few seconds between calls. Fetch categories one after another, not concurrently.

## Phase 2 - Diverge (read each paper in isolation)

For every paper collected in Phase 1, spawn a **parallel** Agent/Task call. One per paper. Each agent gets only:

- the build problem
- that ONE paper's title, abstract, authors, year, and no other paper
- the instruction below

> You are in DIVERGENT READ mode. You have exactly one paper's title and
> abstract, and one build problem. You do not know what other papers
> exist. Do not assume, invent, or gesture at a broader survey.
> Read this abstract as if scouting prior art for someone about to build
> the stated thing from scratch. Never quote the abstract verbatim beyond
> a few consecutive words; paraphrase in your own words.
> Extract: approach (1-2 sentences, the core mechanism), borrow (1
> sentence, the single most concrete implementable takeaway, imperative:
> "Use X to do Y"; if too tangential, say so plainly), limitation (1
> sentence, the load-bearing weakness or breaking condition), relevanceNote
> (1 short clause on fit to the stated problem).
> Output JSON only: `{"approach":"...","borrow":"...","limitation":"...","relevanceNote":"..."}`

**Critical invariant.** These calls must be parallel and isolated. A read that has seen other papers' abstracts starts summarizing the SET instead of grounding in the ONE paper in front of it. That failure is easy to miss, because the output still looks paper-specific.

## Phase 3 - Converge (one path, not a shortlist)

After all reads return:

1. **Score.** Rate each reading 0-10 on relevance (fit to the stated problem), practicality (buildable by a small team without exotic infra), and rigor (does the abstract itself show real evidence, such as benchmarks, proofs, or a shipped system, versus pure concept). Flag a "trap" when a paper's own stated limitation implies a failure mode a builder would otherwise rediscover the hard way. Always pair it with a "strength", the one concrete thing that paper's approach gets right.
2. **Cluster.** Group readings into 3-6 clusters by underlying architectural angle, not by paper and not by keyword: "cache-invalidation plays", "consensus-free plays", "learned-index plays".
3. **Pick ONE.** Choose the cluster with the strongest relevance plus practicality combination. Not the most novel, not the most cited, the one an engineer should actually build. This is the point of departure from wide-open brainstorming: commit to a single recommendation, because "here are 4 papers, you decide" is exactly the time-wasting this loop exists to prevent.
4. **Synthesize.** For the chosen cluster, produce a 4-8 sentence implementation sketch (actionable, not a lit-review summary), citations (paper id, title, url, and role: "primary mechanism", "supporting evidence", or "failure mode to avoid", grounded only in fetched data), the first concrete step, the load-bearing risk, and an "avoid" list pulled from every paper's limitation. Not just the winner's: a pitfall named by a paper in a rejected cluster is still worth avoiding.
5. **Name the runner-ups.** One honest sentence per non-chosen cluster on the real trade-off that lost it the pick. Not a dismissal; the builder should be able to switch paths later knowing why.
6. **One open thread.** A question the read papers raise but do not answer, worth a design-review checkpoint before shipping.

## Result shape

Produce these six pieces, then fold them into the parent report as `SKILL.md` describes. Do not emit them as a standalone document.

1. **Searched.** Categories, search terms, paper count.
2. **Papers read.** Grouped by cluster. Each paper: id, title, one-line approach, score chips `[rel8 prac6 rig7]`.
3. **Prior-art pitfalls.** Papers whose limitation flags a real trap, listed as watch-outs, not verdicts.
4. **THE PATH.** The one chosen cluster: sketch, citations, first step, load-bearing risk, avoid-list. This is the deliverable. Make it unmissable, not buried under the paper list.
5. **Alternates considered, not chosen.** One line each.
6. **Open thread.** The unanswered question.

## Anti-patterns

- **Cross-contaminated reads.** If a paper's read mentions "compared to the other papers here" or "collectively these show", isolation broke. Discard and re-run that read alone.
- **Hallucinated citations.** Never state a paper detail, number, claim, or result that was not in the fetched abstract. If unsure, re-fetch rather than infer from the title.
- **Shortlist-as-cop-out.** Ending Phase 3 with "here are 3 good options" instead of one recommendation defeats the purpose. Commit.
- **Padding a thin result set.** Zero or few relevant papers is a valid, useful finding. It means the mechanism is either genuinely novel or the search terms were wrong. Say so. Do not stretch tangential papers to look like coverage.
- **Treating a paper's abstract as the whole paper.** The abstract is a pointer, not ground truth about implementation details it does not state. Keep "borrow" and "avoid" items at the level the abstract actually supports.
- **Letting the paper outrank the constraints.** The parent skill still owns the recommendation. If THE PATH conflicts with the user's team size, timeline, or operating budget, say so and recommend the boring approach that fits.

## Calibration

- **How many papers?** Default 4 per category across 3-5 categories, so roughly 12-20 papers. Scale down for narrow or well-known mechanisms (2 per category is enough when the space is small), up for genuinely unclear territory.
- **When to stop widening?** If a category-only retry with terms dropped still returns nothing usable, say so and move on. Do not cascade into unrelated categories chasing a result count.
- **Cost.** 1 categorize, N isolated reads (typically 12-20), 1 score, 1 cluster, 1 converge, so about N+4 agent-shaped calls, plus real arXiv HTTP fetches with a few seconds of courtesy delay between categories. This is why the gate exists.
