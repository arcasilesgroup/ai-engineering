# Example — Next.js page (server component)

Fetches data on the server, validates with zod, renders a typed view.
Demonstrates: ESM imports, `Result<T, E>`-style error handling, no
`any`, schema validation at the trust boundary.

```typescript
// app/markets/[id]/page.tsx
import { z } from "zod";
import { notFound } from "next/navigation";
import { config } from "@/config";

const Market = z.object({
  id: z.string().uuid(),
  symbol: z.string().min(1).max(10),
  lastPrice: z.number().finite(),
});
type Market = z.infer<typeof Market>;

type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

async function loadMarket(id: string): Promise<Result<Market>> {
  const res = await fetch(`${config.marketsApi}/markets/${id}`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) {
    return { ok: false, error: new Error(`upstream ${res.status}`) };
  }
  const parsed = Market.safeParse(await res.json());
  return parsed.success
    ? { ok: true, value: parsed.data }
    : { ok: false, error: parsed.error };
}

export default async function Page(
  { params }: { params: { id: string } },
) {
  const result = await loadMarket(params.id);
  if (!result.ok) notFound();
  const { value: market } = result;
  return (
    <article>
      <h1>{market.symbol}</h1>
      <p>{market.lastPrice}</p>
    </article>
  );
}
```

## TDD pairing

```typescript
// app/markets/[id]/page.test.ts
import { describe, it, expect, vi } from "vitest";
import { loadMarket } from "./page";

describe("loadMarket", () => {
  it("returns ok when upstream returns valid market", async () => {
    const fakeId = "abc-123";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: fakeId, symbol: "BTC", lastPrice: 65000 }),
    }));
    const r = await loadMarket(fakeId);
    expect(r.ok).toBe(true);
  });
});
```
