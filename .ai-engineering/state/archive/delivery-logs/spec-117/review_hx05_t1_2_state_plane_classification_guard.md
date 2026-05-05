# Guard Review: HX-05 T-1.2 State-Plane Classification

## Verdict

- `PASS-WITH-NOTES`

## Findings

- The durable-versus-derived-versus-residue split is internally coherent enough to proceed: `decision-store.json`, `framework-events.ndjson`, and `install-state.json` remain the cross-spec durable core, while `framework-capabilities.json` and `ownership-map.json` stay generated projections rather than peer truth.
- `gate-findings.json`, `watch-residuals.json`, cache entries, and adjacent operator-facing last-run outputs are behaving as residue rather than durable authority, but they remain compatibility-boundary surfaces for `T-1.3`, not free relocation targets.
- The ordered or single-writer families are already identified and partially enforced: `framework-events` appends remain serialized, and the gate-findings plus residual publish family still relies on the explicit locking and publication behavior landed during `HX-04`.
- The ownership boundary with `HX-04` remains intact: kernel execution truth and publish semantics stay upstream, while `HX-05` only classifies residue, event vocabulary, task traces, and derived report behavior.
- Deferred ownership remains clean with adjacent features: task-state semantics stay with `HX-02`, capability authority with `HX-06`, learning-funnel lifecycle with `HX-07`, and eval taxonomy plus score semantics with `HX-11`.
- The most concrete carry-forward risk is physical co-location, not authority confusion: the spec-local `spec-116` audit artifacts are still globally parked under `.ai-engineering/state/`, so `T-1.3` must stay compatibility-first when it defines the reader and path boundary.

## Outcome

- `HX-05` can proceed to `T-1.3`.
- `T-1.3` should carry a compatibility matrix for quasi-authoritative current paths and readers: `gate-findings.json`, residual publication, `framework-capabilities.json`, `ownership-map.json`, and the remaining spec-local audit artifacts still parked in global state.
- `T-1.3` should preserve the ordered-family rules unchanged: `framework-events` stays single-writer, gate-findings and residual outputs stay explicitly published, and derived scorecards or reports remain downstream of authoritative mutations.
- `T-1.3` must not widen into kernel redesign, capability-card cutover, learning-funnel relocation design, or verification-taxonomy work.

## Reopen Check

- No earlier slice must reopen; the remaining issues are compatibility-boundary work inside `HX-05`, not evidence that `HX-01`, `HX-02`, `HX-03`, or `HX-04` landed the wrong contract.