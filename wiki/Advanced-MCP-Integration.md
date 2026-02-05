# MCP Integration

> Extend Claude's capabilities with Model Context Protocol servers.

## What Is MCP?

Model Context Protocol (MCP) is a standard for extending Claude Code with additional capabilities. MCP servers provide:

- Access to external systems (databases, APIs)
- Custom tools and functions
- Integration with services

## Common MCP Servers

| Server | Purpose | Use Case |
|--------|---------|----------|
| Filesystem | Read/write files outside project | Access system files |
| GitHub | Advanced GitHub API | Issues, PRs, Actions |
| Database | Query databases | Direct DB access |
| Sentry | Error monitoring | Debug production issues |
| Slack | Team communication | Notifications, messages |

## Configuration

MCP servers are configured in `.claude/settings.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"]
    }
  }
}
```

## Installing MCP Servers

### GitHub Server

```bash
# Test installation
npx -y @modelcontextprotocol/server-github

# Add to settings.json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

### Filesystem Server

```bash
# Add to settings.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/path/to/allowed/directory"
      ]
    }
  }
}
```

**Note:** Only specify directories Claude should access.

### Database Server

```bash
# PostgreSQL example
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "${DATABASE_URL}"
      }
    }
  }
}
```

## Using MCP Tools

Once configured, MCP tools are available in Claude Code:

```
List all open issues in this repository.
(Uses mcp__github__list_issues)

Query the users table for recent signups.
(Uses mcp__postgres__query)

Read the system config file at /etc/myapp/config.yaml.
(Uses mcp__filesystem__read_file)
```

## Security Considerations

### Principle of Least Privilege

- Only enable MCP servers you need
- Restrict filesystem access to specific directories
- Use read-only database connections when possible

### Environment Variables

Store sensitive values in environment variables:

```json
{
  "env": {
    "GITHUB_TOKEN": "${GITHUB_TOKEN}",
    "DATABASE_URL": "${DATABASE_URL}"
  }
}
```

Set in your shell:
```bash
export GITHUB_TOKEN="your-token"
export DATABASE_URL="postgres://..."
```

### Audit MCP Usage

Review what MCP tools Claude uses:
- Check conversation history
- Monitor API usage
- Review access logs

## Custom MCP Servers

Create your own MCP server for internal systems:

```typescript
// my-mcp-server/index.ts
import { Server } from "@modelcontextprotocol/sdk/server";

const server = new Server({
  name: "my-company-server",
  version: "1.0.0",
});

server.addTool({
  name: "get_user",
  description: "Get user details from internal system",
  inputSchema: {
    type: "object",
    properties: {
      userId: { type: "string" }
    },
    required: ["userId"]
  },
  handler: async ({ userId }) => {
    // Your implementation
    return { name: "John", email: "john@company.com" };
  }
});

server.start();
```

Configure in settings.json:

```json
{
  "mcpServers": {
    "internal": {
      "command": "node",
      "args": ["/path/to/my-mcp-server/index.js"]
    }
  }
}
```

## Troubleshooting

### Server Not Starting

1. Check command exists: `npx -y @modelcontextprotocol/server-github`
2. Verify environment variables are set
3. Check permissions for filesystem paths

### Tools Not Appearing

1. Restart Claude Code after config changes
2. Verify settings.json syntax is valid
3. Check server logs for errors

### Authentication Errors

1. Verify tokens are valid
2. Check token permissions
3. Ensure environment variables are exported

## MCP Resources

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Official MCP Servers](https://github.com/modelcontextprotocol/servers)
- [MCP SDK](https://github.com/modelcontextprotocol/sdk)

---
**See also:** [Parallel Work](Advanced-Parallel-Work) | [Custom Skills](Customization-Custom-Skills)
