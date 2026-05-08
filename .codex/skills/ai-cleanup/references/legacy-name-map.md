# Legacy → canonical slash command map

Reference table for the spec-127 D-127-04 rename + merger wave. Per
D-127-04, **no alias dispatcher exists** for renamed skills — the new name
is the only name. This file is the *only* migration aid: when an operator
types a legacy form, suggest the new name with the one-line rationale and
stop. Do not use this table to alias-route execution.

This map was previously surfaced by the standalone `/ai-help` skill; that
skill was demoted in Wave 8 (D-127-10 strict surface count) and the
matchback content moved here as a reference. Read this file when someone
types a legacy slash command after the rename.

## /ai-dispatch → /ai-build

D-127-11 — `/ai-build` is the canonical implementation gateway.

## /ai-canvas → /ai-visual

D-127-05 — `/ai-visual` carries the broader visual category framing.

## /ai-market → /ai-gtm

Clearer go-to-market framing; `gtm` is the industry-standard verb.

## /ai-mcp-sentinel → /ai-mcp-audit

Verb-noun naming: audit is the action; sentinel was the metaphor.

## /ai-entropy-gc → /ai-simplify-sweep

No metaphor; sweep == repeated simplify against the live surface.

## /ai-instinct → /ai-observe

Verb-noun; observe is what the skill actually does (no instinct claim).

## /ai-skill-evolve → /ai-skill-tune

Tune is the operation; evolve overpromised what the skill delivers.

## /ai-platform-audit → /ai-ide-audit

We audit IDE wiring, not platforms; the rename matches the scope.

## /ai-run → /ai-autopilot --backlog --source <github|ado|local>

D-127-12 — single autonomous wrapper; `/ai-run` was the legacy alias.

## /ai-board-discover → /ai-board discover

Subcommand merger (D-127-10); one skill, two routes via the argument.

## /ai-board-sync → /ai-board sync

Subcommand merger (D-127-10); paired with `/ai-board discover`.

## /ai-release-gate → /ai-verify --release

Mode flag merger (D-127-10); the release gate is a `/ai-verify` mode.
