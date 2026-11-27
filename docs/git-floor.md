# The git floor on every commit route

A commit message is judged by the `commit-msg` hook, and that hook only runs where a commit
is made by hand. Some commits are not: the validation pipeline makes its own fix commits and
can assign a subject after the commit already exists. Those subjects used to reach the branch
unjudged. The rule now runs again at the push, the one door every route crosses.

## The rule

One predicate, asked by two hooks:

| What | Where |
|---|---|
| the eleven accepted types and the `type(scope): description` shape | [`src/floor/index.ts:167`](../src/floor/index.ts#L167) |
| the verdict both hooks share | [`src/floor/index.ts:170`](../src/floor/index.ts#L170) |
| asked when a commit message is written | [`src/floor/index.ts:185`](../src/floor/index.ts#L185) |
| asked again over the commits a push introduces | [`src/floor/index.ts:314`](../src/floor/index.ts#L314) |

The push asks about the commits that push introduces: the new tips, minus what the remote
already has, minus the base the branch inherits, merge commits excepted. Judging the
inherited history would refuse a push over commits the pusher did not write and cannot
rewrite.

The shims that carry the hooks into a repository are
[`templates/git-commit-msg.tpl:10`](../templates/git-commit-msg.tpl#L10) and its pre-push
sibling; `ai-eng` installs all three from one list in
[`src/floor/template.ts:8`](../src/floor/template.ts#L8).

## The routes, and which ones run the rule

| Route | Who writes the commit | `commit-msg` runs? | Judged by |
|---|---|---|---|
| A person or an agent commits in a checkout | `git commit` | yes | the `commit-msg` hook |
| A pipeline fix commit (`review`, `test`, `document`, `lint`, …) | the pipeline itself | no — it writes the commit, no hook is offered a say | `pre-push` |
| A pipeline subject rewrite | the pipeline, after the commit exists | no — the subject is assigned afterwards | `pre-push` |
| The evidence branch | the pipeline | no | `pre-push`, and only when this repository enables `test.evidence.store_in_repo` |
| A CI repair commit (`ci`) | the pipeline, through a plain `git commit` in the run worktree | yes | the `commit-msg` hook |
| Syncing the base into a branch (`git merge origin/main`, or a rebase onto it) | the base's own authors, and `git` for the merge commit | for a merge made here, yes | `pre-push`, over the commits the push introduces: the base's history is out of range, and merge commits are a bypass (below) |

The `ci` row is the odd one out, and it is why the rule looked like it ran on some routes and
not others: the CI repair is the only pipeline route that hands the commit to `git` instead of
assembling it. Everything else went around the hook.

## The evidence

Recorded run of [PR #823](https://github.com/arcasilesgroup/ai-engineering/pull/823)
(`fm/aie-filter-annotate`, run `01M84H2Y4395R8PP1894PFCE0M`), read back from the pipeline's own
step logs under `$NM_HOME/logs/01M84H2Y4395R8PP1894PFCE0M/`:

- `ci.log:115`, `ci.log:243`, `ci.log:351`, `ci.log:473` — the CI repair route tried
  `git commit -m no-mistakes(ci): …` and the hook answered
  `the message does not follow the Conventional Commits convention`. Four attempts, four
  refusals, one per fix round.
- `review.log:241`, `review.log:359`, `document.log:172` — `committed agent fixes:
  no-mistakes(review): …` and `… no-mistakes(document): …`: three commits with the same
  invalid type, no hook, no refusal. They are `017588d4`, `95518e0c` and `e9071e43` on `main`.
- `ci.log:557` — `applied commit settings to 1 agent commit(s)`: the rewrite route, which
  replaced the subject of a commit the agent had already made.

Reproduced outside the pipeline with the shims installed: a `git commit --no-verify -m
"no-mistakes(review): …"` followed by `git push` exited 0 before this change, and the push is
refused after it. `tests/floor-gates.spec.ts` drives both, over a published base and a
feature branch, and asserts the exact refusal.

## What a refusal looks like now

```
pre-push: e82dcfa702a5 does not follow the Conventional Commits convention: "no-mistakes(review): fix findings counts"
Format: type(scope): description — rewrite that commit's subject before pushing.
```

The commit is not lost and nothing is rewritten for you: `git commit --amend` on the tip, or an
interactive rebase for a commit further back, then push again.

Rewriting only works for a commit you made. On the pipeline routes — the fix commit and the
subject rewrite — the pipeline writes the subject, so an amend does not stick: pin
`commit.fix_message` in `.no-mistakes.yaml` to a subject the floor accepts, replacing the
pipeline default `no-mistakes({{.Step}}): {{.Summary}}`. This repository pins
`chore({{.Step}}): {{.Summary}}`, and `tests/pipeline-commit-routes.spec.ts` holds every route
it turns on to that pin.

## No route is exempt

A route that cannot be hooked is not excused from the rule, it is judged later. The only route
this repository does not turn on is the evidence branch, and turning it on requires pinning
`test.evidence.commit_message` to a subject the floor accepts; until then it is not a route
here at all. Whichever route is added next, the push asks the question.

Syncing the base into a branch is where judging later has a limit, and the limit is ownership:
a `git merge origin/main` pulls the base's commits into the branch, the pusher did not write
them, and rewriting them would rewrite published history that belongs to the base. So the push
judges the commits it introduces — the pusher's own — and keeps the base's history out of
range.

Merge commits are a wider exemption, and it is a bypass rather than coverage. The push skips
every merge commit, whoever wrote its subject, because git writes that subject in the ordinary
flow. A merge subject is judged only by `commit-msg`, and only when the merge is made in this
clone with the hooks installed: a merge made elsewhere, or with `--no-verify`, reaches the
branch with no judgement at all. That is the one hole in this rule, and it is named here so it
cannot be mistaken for a covered route.

A bad subject is refused while the commit is still the pusher's own. Once it lands on the base
it is inherited history and falls out of range — which is why the three `no-mistakes(review):`
and `no-mistakes(document):` commits in the record above, now on `main`, are no longer caught:
the gate stops a bad subject on its first push, it does not clean up history that is already
published.

Two tests hold that:

- [`tests/floor-gates.spec.ts`](../tests/floor-gates.spec.ts) — a commit whose subject the
  `commit-msg` hook would reject cannot be pushed even when no hook saw it, a conventional
  subject on the same push still passes, a push whose outgoing commits cannot be read is
  refused instead of waved through, and a branch that merges an advanced base whose own
  commits break the convention is pushed once the pusher's own commits keep it.
- [`tests/pipeline-commit-routes.spec.ts`](../tests/pipeline-commit-routes.spec.ts) — every
  route this repository's `.no-mistakes.yaml` turns on renders a subject the floor accepts, for
  every pipeline step, and a commit-subject template the suite does not know how to render
  fails it.
