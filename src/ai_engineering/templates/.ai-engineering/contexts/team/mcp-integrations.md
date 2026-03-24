# MCP Integrations

Approved MCP servers and their usage patterns, security posture, and compliance classification.

## Context7 (Documentation Lookup)

**What**: Open-source MCP server for live library documentation. Queries up-to-date docs for any library without leaving the IDE.

**How**: Two-step protocol:
1. `resolve-library-id` -- resolve a library name to its Context7-compatible ID
2. `query-docs` -- retrieve documentation for that library

Limit to a maximum of 3 MCP calls per question. If the answer is not found in 3 calls, fall back to existing knowledge.

**Setup**:
```bash
# NPX (simplest)
npx @upstash/context7-mcp

# Docker (air-gapped / enterprise)
docker run -p 3000:3000 upstash/context7-mcp
```

**Security**: Only the library name and query string leave the machine. No source code, no project structure, no PII is transmitted. Self-hostable via Docker for air-gapped environments.

**Compliance classification**:

| Environment | Risk | Notes |
|-------------|------|-------|
| Standard enterprise | LOW | Only library names sent externally |
| Air-gapped / regulated | LOW | Self-host via Docker; zero external calls |

**Mandatory rule**: No sensitive data in queries. Library names and technical questions only.

## Exa Search

**What**: Neural search engine accessible via MCP. Provides semantic web search, code context, company research, and deep research capabilities.

**Tools** (7):

| Tool | Purpose |
|------|---------|
| `web_search` | General web search with neural ranking |
| `web_search_advanced` | Search with filters (domain, date, type) |
| `get_code_context` | Find code examples and technical context |
| `company_research` | Company information and analysis |
| `people_search` | Public professional information |
| `crawling` | Extract content from specific URLs |
| `deep_researcher` | Multi-step research with synthesis |

**Setup**:
```bash
export EXA_API_KEY="your-api-key"
```

**Security**: All queries are sent to Exa's servers for processing. Apply these rules:
- No client data in queries
- No internal project names or codenames
- No PII (names, emails, account numbers)
- No proprietary business logic descriptions
- Queries should be phrased as generic technical or market questions

**Compliance classification**:

| Environment | Risk | Notes |
|-------------|------|-------|
| Standard enterprise | MEDIUM | Queries leave network; review data classification |
| Regulated (banking, healthcare) | MEDIUM-HIGH | Requires data classification review per deployment |
| Air-gapped | NOT AVAILABLE | Requires internet; no self-host option |

**Cost**: Credit-based, pay-per-search. Monitor usage to avoid unexpected spend.

**Mandatory rule**: Before each query, verify it contains no client data, no internal project names, and no PII. When in doubt, rephrase as a generic question.

## fal.ai (Media Generation)

**What**: AI media generation platform accessible via MCP. Provides image, video, and audio generation models. Used by the `ai-media` skill.

**Models**:

| Model | Type | Use Case |
|-------|------|----------|
| `fal-ai/nano-banana-2` | Image (fast) | Iterations, drafts, inpainting |
| `fal-ai/nano-banana-pro` | Image (quality) | Production images, typography |
| `fal-ai/seedance-1-0-pro` | Video | Text/image to video |
| `fal-ai/kling-video/v3/pro` | Video + audio | Video with native audio |
| `fal-ai/veo-3` | Video + audio | Highest visual quality |
| `fal-ai/csm-1b` | Audio TTS | Conversational speech |
| `fal-ai/thinksound` | Audio (video-to-audio) | Sound design from video |

**Setup**:
```json
{
  "mcpServers": {
    "fal-ai": {
      "command": "npx",
      "args": ["-y", "fal-ai-mcp"],
      "env": { "FAL_KEY": "your-fal-key" }
    }
  }
}
```

**Security**: Prompts and generated media pass through fal.ai servers. No source code is transmitted. Generated assets are returned as URLs with limited TTL.

**Compliance classification**:

| Environment | Risk | Notes |
|-------------|------|-------|
| Standard enterprise | LOW | Only creative prompts sent; no code or data |
| Regulated | LOW-MEDIUM | Review prompt content if generating branded/client material |
| Air-gapped | NOT AVAILABLE | Requires internet |

**Cost**: Per-generation pricing. Use `estimate_cost()` before video generations. Iterate with cheaper models (nano-banana-2) before committing to expensive ones (veo-3).

**Mandatory rule**: Estimate cost before generating video. Use progressive quality pattern: cheap model for iterations, expensive model for finals only.
