# Evaluation Framework

## Purpose

Validate that review skills produce correct and consistent findings across benchmark scenarios.

## Structure

```
evals/
├── README.md           # This file
├── registry.json       # Benchmark registry
└── benchmarks/         # Individual benchmark scenarios (future)
    └── .gitkeep
```

## Benchmark Format (Future)

Each benchmark contains:
- `metadata.json` — source, title, description, expected findings
- `diff.patch` — frozen diff to review
- `expected.json` — expected findings with severity and category

## Running Evaluations (Future)

```bash
ai-eng eval run [--benchmark <name>] [--dimension <security|performance|...>]
ai-eng eval score [--format json|table]
ai-eng eval report
```

## Scoring

Matching logic: file + line proximity + keyword overlap.
- True positive: finding matches expected
- False positive: finding not in expected
- False negative: expected finding not found
