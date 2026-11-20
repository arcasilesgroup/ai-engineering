# Layer rules

Load this in phase (e), when the repository has code and its layer rules are missing or out of date.

Choosing layers is judgement. Base it on evidence, in this order:

1. **The real graph.** Map who imports whom with CodeGraph (`/ai-codegraph`) when the repo is indexed, otherwise with the language's own tool. Name the folders that exist and the directions that already hold.
2. **The stack's guidelines.** Look up how this language and framework layer an application (`/ai-research`): the framework's own docs first, then Clean or hexagonal architecture where the project's size earns it. Cite each source on the page.
3. **The project's documents.** AGENTS.md, DECISIONS.md and the README say what the people here already decided. They win over a general guideline.

## The tool per language

| Language | Tool | Rules live in | Runs from |
| --- | --- | --- | --- |
| TypeScript / JavaScript | dependency-cruiser | `.dependency-cruiser.cjs` | an `arch` script in `package.json` |
| Python | import-linter | `[tool.importlinter]` in `pyproject.toml`, or `.importlinter` | `lint-imports` |
| Go | depguard in golangci-lint | `.golangci.yml` | `golangci-lint run` |

Another language: propose its standard tool and name it as a new choice on the page.

## How the rules reach CI

In a JavaScript project the ai-eng check workflow runs a declared `arch` script, so the `package.json` line is enough. For any other language the workflow does not run the tool: put the command in a CI step the project already has, and say on the page which step that is.

## Writing the rules

Layers come from folders that exist here. Each rule forbids a direction that is clean today, so the first run passes and the next wrong import fails. A rule the code already breaks goes on the page as a finding, with the imports that break it, never as a rule that fails on day one. A second run starts from the files on disk and adds only what changed.
