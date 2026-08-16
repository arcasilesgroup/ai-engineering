# Architecture

The heuristics of the advisor this project decided not to ship. A separate advisor
duplicates the judgement and the output, so the judgement happens twice: here, against a
diff, and in `/ai-spec`, against a decision that has not been made yet.

- The boundary the change crosses, and whether it should have. The hooks never import the
  package, the presentation is a leaf and the policy stays data.
- A dependency added where the stack already had an answer. Name the answer that was
  missing, or the dependency is a preference.
- State that now lives in two places, and which of them a reader would believe.
- The cost of reversing it. A diff that makes a decision a later diff cannot unmake belongs
  in a spec before it belongs in code.
- Coupling accepted for reuse nobody has asked for yet.
- Whether this is a decision at all. If it is, `/ai-spec` owns it, and a review that
  silently ratifies one is how a project acquires decisions nobody took.
