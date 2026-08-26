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
    },
    {
      "id": "036",
      "kind": "spec",
      "path": "specs/036-validate-adoption-and-close-boundary-delta/spec.md",
      "target_digest": "sha256:40491ca7199838f22f903c03ea28716589dfa0c0434a8252d34d9f0dcada130a"
    },
    {
      "id": "037",
      "kind": "spec",
      "path": "specs/037-model-router-and-intake-validation/spec.md",
      "target_digest": "sha256:875f3fd5ff037257f159b5b029946a4736846037ee1dee10284522b1bca658f2"
    },
    {
      "id": "038",
      "kind": "spec",
      "path": "specs/038-design-accessibility-guard/spec.md",
      "target_digest": "sha256:567a29d216b9508878b75efb8e63bb264f3d1abc72584ef36351cd65fccbde6e"
    }
  ],
  "schema": "urn:ai-engineering:intent:1",
  "schema_version": "1",
  "solution_intent": {
    "current_facts": [
      "Spec 010's P0 wave landed; its P1-P5 waves, a URL, a deployment, a pilot and any compliance claim remain unproven by this record.",
      "Specs 035-038 record the reference-adoption block: 035 was superseded by 036 when the pre-build audit proved eight of the nine research patterns already shipped in specs 013-034; 036 validated them and added the decision-boundary classifier (U0/U1, CANNOT DECIDE).",
      "037 built the P0 roadmap rows: per-repository model tiers in the pin (top/medium/low/default_tier), a step router (mechanical to low, hard reasoning to top), the validated intake (goal, constraints, acceptance) and the registered 16-point roadmap.",
      "038 built the accessibility floor into the design gateway: a designed surface names the four basics (contrast, keyboard, focus, reduced-motion) or exits not-covered with a reason; a silent pass is refused.",
      "The gate runs 2365 passed with only the four inherited test_madr.py failures (ADR 0025); the skill-routing baseline is 369.",
      "The audit chain carries 22 broken links (918-977): ai-eng audit verify stays FAIL until a person at a keyboard runs ai-eng audit account --range 918-977."
    ],
    "fixed_constraints": [
      "Guards fail closed; telemetry observes and never decides.",
      "Models may investigate, propose and review; only a human or an approved versioned policy supplies authority.",
      "Never record, publish or transmit secrets, personal data or private material.",
      "Until a separately approved P3 plan proves safe coordination, one writer owns repository changes.",
      "Model tiers live in the repository's pin; the framework never hardcodes a model name or provider."
    ],
    "intended_outcomes": [
      "Govern human-led and bounded autonomous engineering from Solution Intent through executed evidence and production.",
      "Expose missing authority, missing evidence and false-green results as blocking INCOMPLETE or FAIL outcomes.",
      "The governed cycle routes each step to the repository's configured model tier, and a goal starts from a validated intake.",
      "Every designed surface meets the accessibility floor or exits not-covered with a reason."
    ],
    "variables": [
      "The reviewed implementation increment may change within the normative P0-P5 target.",
      "Tools and agent surfaces may change only while their declared capability boundaries remain truthful.",
      "The accessibility floor (landmarks, screen-reader labels, tab order) may grow with measured need."
    ]
  },
  "type": "intent"
}