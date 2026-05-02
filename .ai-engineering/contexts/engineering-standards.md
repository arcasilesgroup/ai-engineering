# Engineering Standards Matrix

Canonical late-wave standards surface for implementation, review, verification, and retirement governance. The Constitution remains the hard-rule surface; `operational-principles.md` remains the concise operational principle surface. This matrix binds those principles to review and verify consumers.

## Standards

| Standard ID | Canonical rule | Review binding | Verify binding |
| --- | --- | --- | --- |
| `clean-code` | Code stays readable, cohesive, explicitly named, and easy to change. | correctness, maintainability, frontend, design | quality, platform |
| `clean-architecture` | Policy stays separated from framework, IO, and delivery details when the problem warrants that boundary. | architecture, backend, compatibility | architecture, platform |
| `solid` | Responsibilities and abstractions stay explicit and proportionate. | architecture, maintainability, backend | architecture, quality |
| `dry` | Shared knowledge is centralized when real repetition would otherwise drift. | maintainability, architecture, performance | quality, architecture |
| `kiss` | The simplest design that fully satisfies the approved spec wins. | architecture, maintainability, correctness | quality, feature |
| `yagni` | Speculative extensions wait for real requirements and tests. | architecture, compatibility, maintainability | feature, architecture |
| `tdd` | Domain behavior starts with a failing test and refactors stay green. | testing, correctness, compatibility | quality, feature, platform |
| `sdd` | Implementation traces to approved specs, plans, evidence, and decisions. | architecture, compatibility, testing | governance, feature, platform |
| `harness-engineering` | Deterministic gates, work-plane state, mirrors, context packs, and evals remain governed harness surfaces. | security, architecture, compatibility, testing, performance | governance, security, architecture, platform |

## Consumption Rule

Review and verify surfaces consume this matrix through `ai_engineering.standards`. Do not restate a separate standards canon in skills, agents, or root docs. Link here and add only consumer-specific instructions.

## Retirement Rule

Legacy deletion is governed by the family manifest in `ai_engineering.standards`. A family can retire only when it has a replacement owner, parity proof, rollback path, and explicit serialized sequence.