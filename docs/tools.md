# The binaries each stack needs

`ai-eng init` detects some of these, prints the line that installs each, and installs
nothing. An installer that also installs your toolchain is doing two jobs, and generating
code inside an installer is how the previous version reached 9,910 lines.

Azure DevOps works and is not a CLI surface, because a YAML file in an Azure Repos
repository is inert until a human registers a pipeline, its `pr:` block is ignored, and the
pipeline's UI settings can override the file's triggers silently. Commit the same steps as
`azure-pipelines.yml`, register it under Pipelines → Existing YAML file, then add it as
required build validation in the branch policy for the default branch — that last step, not
the `pr:` block, is what makes it run on a pull request, and it is also T0.

## Everywhere, whatever the language

Two of these genuinely are language-agnostic, and the shipped `security` recipe is exactly
those two. Static analysis needs a rule set per language and this project does not ship a
credible cross-language one, so that line is yours to add.

| Binary | What it does | Install |
|---|---|---|
| `just` | runs the recipes CI runs | `brew install just` · `cargo install just` |
| `gitleaks` | secrets, staged and in the tree | `brew install gitleaks` |
| `trivy` | dependencies, licences and misconfiguration — 13 ecosystems plus Terraform, Kubernetes and Dockerfiles | `brew install trivy` |
| `semgrep` | static analysis; bring your own rules, or ours at `policy/semgrep.yml` | `uv tool install semgrep` |
| `zizmor` · `actionlint` | workflow security and syntax — a language too, and the most attacked one | `uv tool install zizmor` · `brew install actionlint` |

## Per stack

`init` prints a line for the stacks marked **detected**. The rest are documented here and
detected by nothing — the same discipline `policy/surfaces.toml` applies to agent surfaces,
where documented is never reported as proven.

| Stack | Detected by | Build · lint · test |
|---|---|---|
| Python | **detected** — `pyproject.toml` | `uv build` · `ruff check` · `pytest` |
| Node / TypeScript | **detected** — `package.json` | `pnpm build` · `eslint` · `vitest run` |
| Go | **detected** — `go.mod` | `go build ./...` · `golangci-lint run` · `go test ./...` |
| Rust | **detected** — `Cargo.toml` | `cargo build` · `cargo clippy` · `cargo test` |
| Java | **detected** — `pom.xml`; Gradle documented only | `mvn package` · `mvn checkstyle:check` · `mvn test` |
| Ruby | **detected** — `Gemfile` | `bundle exec rake build` · `rubocop` · `rspec` |

Detected by nothing, and each works identically once you have written its three recipes:
.NET (`dotnet build` · `dotnet format --verify-no-changes` · `dotnet test`), PHP, Elixir,
Swift, Kotlin and Terraform.

Detection only decides what `init` prints. Every stack above gets the same floor: the
three git hooks, the guards, the specs and the record.

## A lockfile is not optional

Dependencies with no lockfile beside them make the vulnerability scan silently empty —
nothing is pinned to look up, and that has the same shape as a clean result. Add the check
to your own `security` recipe; this repository enforces it on itself and does not install
that file into yours.
