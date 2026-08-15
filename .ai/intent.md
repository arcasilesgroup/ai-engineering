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
    "accountable_role": "repository maintainer"
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
      "Spec 010 is draft: its P0 wave landed and supersedes spec 004, and its own plan reserves shipped until a candidate proves exact-HEAD CI receipts, which do not exist.",
      "P0 built the verifier for the eight production-ready boxes and earned no receipt for any of them, so every box is INCOMPLETE.",
      "No P1-P5 wave, URL, deployment, pilot or compliance claim is proven by this record."
    ],
    "fixed_constraints": [
      "Guards fail closed; telemetry observes and never decides.",
      "Models may investigate, propose and review; only a human or an approved versioned policy supplies authority.",
      "Never record, publish or transmit secrets, personal data or private material.",
      "Until a separately approved P3 plan proves safe coordination, one writer owns repository changes."
    ],
    "intended_outcomes": [
      "Govern human-led and bounded autonomous engineering from Solution Intent through executed evidence and production.",
      "Expose missing authority, missing evidence and false-green results as blocking INCOMPLETE or FAIL outcomes."
    ],
    "variables": [
      "The reviewed implementation increment may change within the normative P0-P5 target.",
      "Tools and agent surfaces may change only while their declared capability boundaries remain truthful."
    ]
  },
  "type": "intent"
}
