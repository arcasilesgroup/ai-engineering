{
  "identity": {
    "id": "governed-agentic-engineering",
    "title": "Governed agentic engineering"
  },
  "lifecycle": {
    "approval": {
      "approval_ref": "ae523990",
      "approved_at": "2026-08-15T03:54:12Z",
      "authority_role": "repository owner"
    },
    "status": "active",
    "transitions": [
      {
        "approval_ref": "ae523990",
        "authority_role": "repository owner",
        "changed_at": "2026-08-15T03:54:12Z",
        "from": "draft",
        "to": "active"
      }
    ]
  },
  "ownership": {
    "accountable_role": "repository owner"
  },
  "relations": [
    {
      "id": "010",
      "kind": "spec",
      "path": "specs/010-governed-agentic-engineering-foundation/spec.md",
      "target_digest": "sha256:364d83c56c7d9e7b4e2aeb975c9ada5c7b0db6822d79eb939e9010b9417e75db"
    }
  ],
  "schema": "urn:ai-engineering:intent:1",
  "schema_version": "1",
  "solution_intent": {
    "current_facts": [
      "The writing and design surfaces are shipped (037-046). The orphan layer spec 042 deferred was deleted by 044; the per-module verdict with reopening conditions lives in docs/notes/ponytail-orphan-verdicts.md.",
      "The gate is green on main: test_madr 37 passed (ADR 0025 closed), audit verify exits 0, skilleval 428 delta 0. The 024 fidelity audit records what the tree does and does not carry."
    ],
    "fixed_constraints": [
      "Guards fail closed; telemetry observes and never decides.",
      "Models may investigate, propose and review; only a human or an approved versioned policy supplies authority.",
      "Never record, publish or transmit secrets, personal data or private material.",
      "Until a separately approved P3 plan proves safe coordination, one writer owns repository changes. Model tiers live in the repository's pin; the framework never hardcodes a model name or provider."
    ],
    "intended_outcomes": [
      "Govern human-led and bounded autonomous engineering from Solution Intent through executed evidence and production; a governed cycle fits its wall budget — 180 minutes for a giant block, less for normal ones.",
      "Expose missing authority, missing evidence and false-green results as blocking INCOMPLETE or FAIL outcomes.",
      "The governed cycle routes each step to the repository's configured model tier, validates the intake, and every designed surface meets the accessibility floor or exits not-covered."
    ],
    "variables": [
      "The reviewed implementation increment may change within the normative P0-P5 target.",
      "Tools and agent surfaces may change only while their declared capability boundaries remain truthful.",
      "The accessibility floor (landmarks, screen-reader labels, tab order) may grow with measured need."
    ]
  },
  "type": "intent"
}
