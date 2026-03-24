## Protocol Concepts

The Model Context Protocol (MCP) lets AI assistants call tools, read resources, and use prompts from your server.

**Tools** -- Actions the model can invoke (search, run a command, call an API). The primary way to add capabilities.

**Resources** -- Read-only data the model can fetch (file contents, API responses, database records). Handlers typically receive a `uri` argument.

**Prompts** -- Reusable, parameterized prompt templates that clients can surface (e.g., in Claude Desktop's slash commands).

## SDK API

The Node/TypeScript SDK provides `McpServer` as the primary entry point. The registration API has changed across versions -- the SDK may expose `tool()` / `resource()` or `registerTool()` / `registerResource()`. Always verify against the current [MCP docs](https://modelcontextprotocol.io) before copying patterns.

**Installation:**

```bash
npm install @modelcontextprotocol/sdk zod
```

**Server setup:**

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

const server = new McpServer({ name: "my-server", version: "1.0.0" });
```

**Registering tools and resources:**

Registration varies by SDK version. Some versions use positional arguments:

```typescript
// Positional: server.tool(name, description, schema, handler)
server.tool("search", "Search the knowledge base", { query: z.string() }, async ({ query }) => {
  const results = await search(query);
  return { content: [{ type: "text", text: JSON.stringify(results) }] };
});
```

Other versions use an options object:

```typescript
// Object: server.tool({ name, description, inputSchema }, handler)
server.tool(
  { name: "search", description: "Search the knowledge base", inputSchema: { query: z.string() } },
  async ({ query }) => {
    const results = await search(query);
    return { content: [{ type: "text", text: JSON.stringify(results) }] };
  }
);
```

Check the official MCP docs or your installed SDK version for the current signature.

## Transport Decision

| Transport | Use Case | Client Examples |
|-----------|----------|-----------------|
| stdio | Local clients, desktop apps | Claude Desktop, local dev |
| Streamable HTTP | Remote clients, cloud deployments | Cursor, cloud services |
| HTTP/SSE (legacy) | Backward compatibility only | Older MCP clients |

**stdio (local):**

Create a stdio transport and pass it to your server's `connect()` method. The exact API varies by SDK version (constructor vs factory). Keep server logic (tools + resources) independent of transport so you can plug in stdio or HTTP in the entrypoint.

**Streamable HTTP (remote):**

For remote clients, use Streamable HTTP (single MCP HTTP endpoint per current spec). Support legacy HTTP/SSE only when backward compatibility with older clients is required.

## Zod Validation

Use Zod schemas for tool input validation. The SDK integrates with Zod natively.

```typescript
// GOOD: explicit schemas with descriptions
server.tool(
  "create_note",
  "Create a new note",
  {
    title: z.string().min(1).max(200).describe("Note title"),
    content: z.string().describe("Note body in markdown"),
    tags: z.array(z.string()).optional().describe("Categorization tags"),
  },
  async ({ title, content, tags }) => {
    const note = await createNote({ title, content, tags });
    return { content: [{ type: "text", text: `Created note: ${note.id}` }] };
  }
);

// BAD: no schema, no descriptions
server.tool("create_note", "Create note", {}, async (input) => {
  // What fields does input have? No validation, no documentation.
});
```

## Best Practices

**Schema first:** Define input schemas for every tool. Document parameters with `.describe()` so the model knows what each field means.

**Structured errors:** Return error messages the model can interpret. Avoid raw stack traces.

```typescript
// GOOD: structured error the model can understand
return { content: [{ type: "text", text: "Error: Note not found. Provide a valid note ID." }] };

// BAD: raw stack trace
throw new Error(err.stack);
```

**Idempotency:** Prefer idempotent tools where possible so retries are safe (e.g., "upsert" instead of "create if not exists then fail").

**Rate and cost awareness:** For tools that call external APIs, document rate limits and costs in the tool description so the model can make informed decisions.

**Versioning:** Pin SDK version in `package.json`. The MCP SDK evolves rapidly -- check release notes when upgrading.

## SDK Availability

| Language | Package | Status |
|----------|---------|--------|
| JavaScript/TypeScript | `@modelcontextprotocol/sdk` (npm) | Primary SDK |
| Go | `modelcontextprotocol/go-sdk` (GitHub) | Official |
| C# | Official C# SDK for .NET | Official |

For non-TypeScript implementations, the protocol spec is the same but the registration API differs. Refer to each SDK's documentation.

**Important:** The MCP SDK is actively evolving. Method names, constructor signatures, and transport APIs may change between versions. Always verify patterns against the current MCP documentation before shipping.

## Common Anti-Patterns

**Tool design:**

- No input schema -- the model guesses at parameters and sends malformed input
- Vague tool descriptions ("does stuff") -- the model cannot decide when to use the tool
- Missing `.describe()` on schema fields -- the model fills parameters incorrectly
- Non-idempotent tools without documenting side effects

**Transport:**

- Hardcoding transport in server logic -- makes it impossible to switch between stdio and HTTP
- Using legacy HTTP/SSE for new deployments when Streamable HTTP is available
- Not handling transport disconnection gracefully

**Error handling:**

- Throwing raw exceptions instead of returning structured error content
- Returning generic "something went wrong" -- the model cannot self-correct
- Not logging errors server-side for debugging

**Versioning:**

- Copying SDK patterns from examples without checking the installed version
- Not pinning SDK version -- `npm update` silently breaks registration calls
- Ignoring deprecation warnings in SDK output
