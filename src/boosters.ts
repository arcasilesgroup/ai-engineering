// src/boosters.ts — third-party harness boosters offered at init (§14.1).
// ai-eng PRINTS the install command; it never installs, never bundles, never
// executes third-party binaries. What asks no permission does not get installed.

export type Booster = { id: string; label: string; hint: string; command: string };

export type BoosterGroup = { title: string; items: Booster[] };

export const BOOSTER_GROUPS: BoosterGroup[] = [
  {
    title: "Context — fewer tokens per turn",
    items: [
      { id: "rtk", label: "rtk", hint: "compress bash output (60-90% fewer tokens)", command: "brew install rtk && rtk init" },
      { id: "caveman", label: "caveman", hint: "ultra-compressed agent output (-65% tokens)", command: "npx skills add caveman" },
      { id: "engram", label: "engram", hint: "persistent agent memory across sessions", command: "npx skills add engram" },
    ],
  },
  {
    title: "Design — UI that doesn't look AI-generated",
    items: [
      { id: "impeccable", label: "impeccable", hint: "frontend design + redesign with taste", command: "npx skills add impeccable" },
      { id: "hallmark", label: "hallmark", hint: "anti-AI-slop audit (58 gates)", command: "npx skills add hallmark" },
      { id: "shadcn", label: "shadcn", hint: "component registry with tokens", command: "npx shadcn@latest init" },
      { id: "emil-design-eng", label: "emil-design-eng", hint: "fluid UI polish & invisible details", command: "npx skills add emil-design-eng" },
      { id: "ui-ux-pro-max", label: "ui-ux-pro-max", hint: "premium UX/UI direction", command: "npx skills add ui-ux-pro-max" },
      { id: "tasteskill", label: "tasteskill", hint: "design taste presets", command: "npx skills add tasteskill" },
    ],
  },
  {
    title: "Research — real evidence, not memory",
    items: [
      { id: "tavily", label: "tavily", hint: "current web search & extraction", command: "npx skills add tavily" },
      { id: "exa", label: "exa", hint: "semantic web discovery", command: "npx skills add exa" },
      { id: "context7", label: "context7", hint: "version-aware library docs", command: "npx skills add context7" },
    ],
  },
  {
    title: "Security",
    items: [
      { id: "mantis", label: "mantis", hint: "15-stage security review pipeline (Google)", command: "npx skills add google/mantis" },
    ],
  },
  {
    title: "Harness diagnostics",
    items: [
      { id: "skill-map", label: "skill-map", hint: "map of skills/hooks/agents: collisions, orphans, tokens", command: "npm i -g @skill-map/cli && sm scan" },
    ],
  },
];

/** The exact install lines for what the user ticked, in catalog order. */
export function printCommands(selectedIds: string[]): string[] {
  const flat = BOOSTER_GROUPS.flatMap((group) => group.items);
  return selectedIds
    .map((id) => flat.find((booster) => booster.id === id)?.command)
    .filter((command): command is string => Boolean(command));
}
