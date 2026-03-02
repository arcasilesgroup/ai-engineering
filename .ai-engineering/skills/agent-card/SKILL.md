---
name: agent-card
description: "Generate platform-portable agent descriptor cards from canonical agent definitions for cross-platform AI agent interoperability."
version: 1.0.0
tags: [agents, portability, interoperability, export, platforms]
metadata:
  ai-engineering:
    scope: read-only
    token_estimate: 800
---

# Agent Card

## Purpose

Generate platform-portable agent descriptor cards from canonical `.ai-engineering/agents/<name>.md` definitions. Enables the same agent definitions to be used across multiple AI platforms (GitHub Copilot, Azure AI Foundry, OpenAI AgentKit, Vertex AI) without manual translation.

## Trigger

- New agent created or existing agent modified.
- Platform integration setup (GitHub Copilot, Azure AI Foundry, etc.).
- Cross-platform consistency audit.
- Agent registration with external platform.

## Procedure

### Step 1 — Read Canonical Definition

Load the agent's `.ai-engineering/agents/<name>.md` file. Extract:
- Frontmatter: name, version, scope, capabilities, inputs, outputs, tags
- Body: Identity, Capabilities, Behavior, Output Contract, Boundaries

### Step 2 — Select Target Platform

Determine target format:
- **github-copilot**: `.github/agents/<name>.agent.md` (Markdown with frontmatter)
- **azure-ai-foundry**: JSON agent manifest (capabilities, tools, permissions)
- **openai-agentkit**: YAML agent spec (name, instructions, tools)
- **vertex-ai**: JSON agent descriptor (display_name, description, tools)

### Step 3 — Transform

Map canonical fields to target schema:

| Canonical Field | GitHub Copilot | Azure AI Foundry | OpenAI AgentKit |
|-----------------|---------------|------------------|-----------------|
| name | filename | agent_name | name |
| Identity | description | system_prompt | instructions |
| capabilities | tools list | skills | tools |
| scope | permissions | access_level | permissions |
| inputs | context | input_schema | parameters |
| outputs | response format | output_schema | response_format |

### Step 4 — Generate Card

Produce the platform-specific agent card file. Include:
- All capabilities mapped to platform tools/skills
- Scope translated to platform permission model
- Referenced skills mapped to available tools
- Behavioral constraints preserved

### Step 5 — Validate Consistency

Cross-check generated card against canonical definition:
- All capabilities represented
- Scope correctly translated (read-only → no write permissions)
- No capabilities added beyond canonical definition
- Boundaries preserved in platform-specific format

## Output Contract

- Platform-specific agent card file(s).
- Consistency validation report: matched/unmatched capabilities.
- Platform coverage matrix: which capabilities map to each platform.

## Governance Notes

- Canonical `.ai-engineering/agents/<name>.md` is always source of truth.
- Generated cards must not add capabilities beyond canonical definition.
- Scope restrictions must be preserved (read-only agent must not get write access).
- Re-generate cards whenever canonical definition changes.
