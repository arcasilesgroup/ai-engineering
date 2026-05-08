# Example — Node service (Bun + Hono)

A tiny HTTP service that demonstrates: ESM-only entry, env validation
at boot, parameterised storage, structured logging without leaking
confidential values.

```typescript
// src/server.ts
import { Hono } from "hono";
import { z } from "zod";
import { drizzle } from "drizzle-orm/bun-sqlite";
import { Database } from "bun:sqlite";

const Env = z.object({
  PORT: z.coerce.number().int().min(1).max(65535).default(3000),
  DB_PATH: z.string().min(1),
});
const env = Env.parse(process.env);

const db = drizzle(new Database(env.DB_PATH));

const app = new Hono();

app.post("/markets", async (c) => {
  const body = await c.req.json();
  const Input = z.object({
    symbol: z.string().min(1).max(10),
    lastPrice: z.number().finite(),
  });
  const parsed = Input.safeParse(body);
  if (!parsed.success) {
    return c.json({ error: parsed.error.flatten() }, 400);
  }
  // Drizzle parameterises every value — no string-built SQL.
  await db.insert(markets).values(parsed.data);
  return c.json({ status: "created" }, 201);
});

export default { port: env.PORT, fetch: app.fetch };
```

## TDD pairing

```typescript
// src/server.test.ts
import { describe, it, expect } from "vitest";
import app from "./server";

describe("POST /markets", () => {
  it("rejects an invalid payload with 400", async () => {
    const req = new Request("http://localhost/markets", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ symbol: "" }),
    });
    const res = await app.fetch(req);
    expect(res.status).toBe(400);
  });
});
```
