# MCP Integrations

Framework-managed MCP guidance for approved servers, data-handling boundaries,
and usage posture.

## Context7

**What**: live library documentation lookup via MCP.

**Protocol**:
1. `resolve-library-id`
2. `query-docs`

Operational rules:
- Limit to 3 MCP calls per question
- If the answer is not found in 3 calls, fall back to existing knowledge
- Never include sensitive project data in the query

**Security**:
- Only library names and technical questions leave the machine
- No source code, project structure, or PII
- Self-hostable via Docker for regulated environments

## Exa Search

**What**: neural web and code-context search via MCP.

**Tools**:
- `web_search`
- `web_search_advanced`
- `get_code_context`
- `company_research`
- `people_search`
- `crawling`
- `deep_researcher`

Operational rules:
- No client data, no internal codenames, no PII
- Rephrase queries as generic technical or market questions when needed
- Review cost before broad research workflows

## fal.ai

**What**: image, video, and audio generation via MCP. Used by `ai-media`.

Operational rules:
- No source code in prompts
- Estimate cost before video generation
- Iterate with cheaper models before using production-grade ones
- Treat returned asset URLs as transient

## Compliance Summary

| Server | Default Risk | Key Rule |
|--------|--------------|----------|
| Context7 | Low | Library names and technical questions only |
| Exa | Medium | No client data, codenames, or PII |
| fal.ai | Low-Medium | Prompt hygiene and cost estimation required |
