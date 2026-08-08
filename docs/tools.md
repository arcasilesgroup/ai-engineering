# The binaries each stack needs

`ai-eng init` detects which of these apply to your repository and prints the line that
installs each one. It installs nothing itself: an installer that also installs your
toolchain is doing two jobs, and generating code inside an installer is how the previous
version reached 9,910 lines.

## Everywhere, whatever the language

Scanners read files, not languages, so the security recipe in the `justfile` is identical
in every repository.

| Binary | What it does | Install |
|---|---|---|
| `just` | runs the recipes CI runs | `brew install just` · `cargo install just` |
| `gitleaks` | secrets, staged and in the tree | `brew install gitleaks` |
| `semgrep` | static analysis against `policy/semgrep.yml` | `uv tool install semgrep` |
| `trivy` | dependency vulnerabilities and licences, 13 ecosystems | `brew install trivy` |
| `zizmor` | workflow security — the most attacked language you run | `uv tool install zizmor` |
| `actionlint` | workflow syntax | `brew install actionlint` |
| `vale` | plain language, against `policy/glossary.yml` | `brew install vale` |

## Per stack

| Stack | Detected by | Build · lint · test |
|---|---|---|
| Python | `pyproject.toml` | `uv build` · `ruff check` · `pytest` |
| Node / TypeScript | `package.json` | `pnpm build` · `eslint` · `vitest run` |
| Go | `go.mod` | `go build ./...` · `golangci-lint run` · `go test ./...` |
| Rust | `Cargo.toml` | `cargo build` · `cargo clippy` · `cargo test` |
| Java | `pom.xml` | `mvn package` · `mvn checkstyle:check` · `mvn test` |
| Ruby | `Gemfile` | `bundle exec rake build` · `rubocop` · `rspec` |
| .NET | `*.csproj` | `dotnet build` · `dotnet format --verify-no-changes` · `dotnet test` |
| PHP | `composer.json` | `composer install` · `phpstan analyse` · `phpunit` |
| Elixir | `mix.exs` | `mix compile` · `mix credo` · `mix test` |
| Swift | `Package.swift` | `swift build` · `swiftlint` · `swift test` |
| Kotlin | `build.gradle.kts` | `gradle build` · `ktlint` · `gradle test` |
| Terraform | `*.tf` | `terraform validate` · `tflint` · `terraform plan` |
| Astro / static | `astro.config.*` | `pnpm build` · `eslint` · `pnpm test` |

## A lockfile is not optional

A manifest that declares dependencies with no lockfile beside it makes the vulnerability
scan silently empty — it has nothing pinned to look up. `tests/anti_theatre.py` fails the
build for exactly that, because a scan that finds nothing because it looked at nothing is
the same shape as a scan that found nothing because there was nothing.
