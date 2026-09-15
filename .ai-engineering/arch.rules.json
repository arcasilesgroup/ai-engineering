# .ai-engineering/arch.rules.json — YOUR real layers, knowledge the agent cannot
# deduce from the import graph (§16). ai-architect proposes diffs as PRs; a human
# approves. bootstrap: an empty repo does not deadlock — the arch tests activate
# when src/ appears.
{
  "layers": {
    "feature": "src/features/**",
    "shared": "src/shared/**",
    "core": "src/core/**"
  },
  "rules": [
    { "from": "feature", "mayNotImport": "feature", "except": "*/index.ts" },
    { "from": "shared", "mayNotImport": "feature" },
    { "any": [], "forbid": "cycles" }
  ],
  "bootstrap": "allow-empty-while-files==0"
}
