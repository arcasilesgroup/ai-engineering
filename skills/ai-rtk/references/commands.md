# rtk command reference

Percentages are **bash output bytes removed**, not bill reduction. Source: rtk `docs/guide/resources/what-rtk-covers.md` and `README.md`. Flags and behavior verified against the **v0.45.0** binary; the percentages themselves are rtk's published figures, not local measurements, except where noted below.

Verified locally on v0.45.0: `rtk read` levels (173,652 B file → 141,737 B minimal, 35,461 B aggressive, unchanged at default), `rtk smart`, `rtk ls`, `rtk grep`, `rtk find`, `rtk err`, `rtk test`, `rtk gain`, `rtk proxy`, `rtk git status/log/diff/add/commit`, and the `rtk rewrite` mapping for ~36 command shapes.

## Files and search

```bash
rtk ls .                        # compact directory tree with file counts   -80%
rtk tree src/                   # tree view
rtk find "*.rs" .               # compact find results                      -75%
rtk grep "pattern" .            # grouped by file, long lines truncated     -70%
rtk rg "pattern" src/           # ripgrep, same filtering
rtk read file.rs                # level none (DEFAULT): full content, 0% saved
rtk read file.rs -l minimal     # comments/blank lines stripped             -20%
rtk read file.rs -l aggressive  # signatures only, bodies stripped          -80%
rtk read file.rs --max-lines 50 # first N lines           (-m is the short form)
rtk read app.log --tail-lines 20 # last N lines
rtk smart file.rs               # 2-line heuristic summary                  -99%
rtk diff a.txt b.txt            # condensed diff (exit 1 if files differ)   -65%
rtk wc file.txt                 # compact counts                            -60%
rtk du -sh . / rtk df           # compact disk usage
```

`cat`, `head`, `tail` map to `rtk read` — except with a redirect (`cat a > b`), which is a write and stays raw.

## Git

| Command | Reduction | What changes |
|---|---|---|
| `rtk git status` | 75-93% | Compact stat format, grouped by state |
| `rtk git log -n 10` | 80-92% | Hash + author + subject only |
| `rtk git diff` | 70% | Context reduced, headers stripped |
| `rtk git show` | 70% | Same as diff |
| `rtk git stash list` | 75% | One line per entry |
| `rtk git add` | — | → `ok 2 files changed, 2 insertions(+)` |
| `rtk git commit -m "msg"` | — | → `ok ca6844d` |
| `rtk git push` | — | → `ok main` |
| `rtk git pull` | — | → `ok 3 files +10 -2` |

Global git options are normalized: `git -C /tmp status` is recognized as `git status`.

## Forges

| Command | Reduction | What changes |
|---|---|---|
| `rtk gh pr list` | — | Compact PR listing |
| `rtk gh pr view 42` | 87% | Drops ASCII art and verbose metadata |
| `rtk gh pr checks` | 79% | Status + name, failures highlighted |
| `rtk gh issue list` / `view` | 80% | Body only, no decoration |
| `rtk gh run list` | 82% | Compact workflow run summary |
| `rtk glab ...` | — | GitLab equivalent |
| `rtk gt log` | 75% | Graphite stack summary |
| `rtk gt status` | 70% | Current branch context |

## Rust

| Command | Reduction | What changes |
|---|---|---|
| `rtk cargo test` | 90% | Failures only, passes collapsed to a count |
| `rtk cargo nextest run` | 90% | Same |
| `rtk cargo build` | 80% | Errors and warnings only |
| `rtk cargo check` | 80% | Errors and warnings only |
| `rtk cargo clippy` | 80% | Lints grouped by file |

## JavaScript / TypeScript

| Command | Reduction | What changes |
|---|---|---|
| `rtk jest` | 94-99% | Failures only |
| `rtk vitest` | 94-99% | Failures only |
| `rtk playwright test` | 90% | Failures + trace links |
| `rtk tsc` | 75% | Type errors grouped by file |
| `rtk lint` / `rtk lint biome` | 84% | Violations grouped by rule/file |
| `rtk prettier --check .` | — | Files needing formatting only |
| `rtk next build` | 80% | Route summary + errors |
| `rtk pnpm list` | 70-90% | Compact dependency tree |
| `rtk pnpm outdated` | 70% | Package + current + latest |
| `rtk npm ...` / `rtk npx ...` | — | Progress noise stripped |
| `rtk prisma generate` / `migrate` | 75% | Status only, no ASCII art |

## Python

| Command | Reduction | What changes |
|---|---|---|
| `rtk pytest` | 80-90% | Failures only, traceback trimmed |
| `rtk ruff check` | 75-80% | Violations grouped by rule and file |
| `rtk mypy` | 75% | Type errors grouped by file |
| `rtk pip list` / `outdated` / `install` | 70% | Installed packages only |
| `rtk uv run pytest` | — | Preserves uv env, keeps program output |
| `rtk poetry ...` | — | Progress stripped |

## Go

| Command | Reduction | What changes |
|---|---|---|
| `rtk go test` | 80-90% | NDJSON parsed, failures only |
| `rtk go build` | 75% | Errors only |
| `rtk golangci-lint run` | 75-85% | JSON parsed, grouped by file |

## Ruby

| Command | Reduction | What changes |
|---|---|---|
| `rtk rspec` | 80-90% | JSON, failures only |
| `rtk rubocop` | 60-75% | Offenses grouped by file |
| `rtk rake test` | 70-90% | Minitest failures only |
| `rtk bundle install` | — | `Using` lines stripped |

## PHP

`rtk php`, `rtk composer`, `rtk phpunit`, `rtk phpstan`, `rtk pest`, `rtk pint`, `rtk paratest`, `rtk ecs`. Vendor paths are normalized — `vendor/bin/phpunit` and `bin/phpunit` are recognized.

## JVM, .NET, other compiled

| Command | Reduction | What changes |
|---|---|---|
| `rtk mvn ...` / `rtk gradlew ...` | — | Build noise stripped, errors kept |
| `rtk sbt test` | 90% | ScalaTest failures only |
| `rtk sbt compile` | 75% | Compilation errors only |
| `rtk sbt run` | — | SBT preamble stripped |
| `rtk dotnet build` | 80% | Errors and warnings |
| `rtk dotnet test` | 85-90% | Failures only |
| `rtk dotnet format` | 75% | Changed files only |
| `rtk swift ...` / `rtk mix ...` / `rtk make ...` | — | Errors kept, noise dropped |

## Containers and orchestration

| Command | Reduction | What changes |
|---|---|---|
| `rtk docker ps` | 65% | Name, image, status, port |
| `rtk docker images` | 60% | Name + tag + size |
| `rtk docker logs <c>` | 70% | Deduplicated, repeats collapsed with counts |
| `rtk docker compose ps` / `up` | 75% | Service status, errors highlighted |
| `rtk kubectl pods` / `get pods` | 65% | Name + status + restarts |
| `rtk kubectl logs <pod>` | 70% | Deduplicated |
| `rtk kubectl services` | — | Compact service list |
| `rtk oc get pods` / `services` / `logs` | — | OpenShift equivalents |
| `rtk helm ...` | — | Compact release output |

## Infrastructure as code

```bash
rtk terraform plan / apply      # compact plan and apply output
rtk tofu ...                    # OpenTofu equivalent
rtk pulumi preview              # header/URL/duration noise stripped
rtk pulumi up / destroy / refresh
rtk pulumi stack                # metadata, owner/timestamps stripped
rtk ansible-playbook ...
rtk liquibase ...
```

## Cloud, network, data

```bash
rtk aws sts get-caller-identity              # one-line identity
rtk aws ec2 describe-instances               # compact instance list
rtk aws lambda list-functions                # name/runtime/memory, secrets stripped
rtk aws logs get-log-events                  # timestamped messages only
rtk aws cloudformation describe-stack-events # failures first
rtk aws dynamodb scan                        # type annotations unwrapped
rtk aws iam list-roles                       # policy documents stripped
rtk aws s3 ls                                # truncated, full output tee'd
rtk gcloud ...                               # -70% JSON condensed
rtk psql -c "..."                            # -65% results without decoration
rtk curl <url>                               # -60% body only, full output saved
rtk wget <url>                               # progress bars stripped
rtk ping <host>                              # compact
rtk rsync ...                                # per-file spam collapsed
```

## Linters and system

`rtk shellcheck`, `rtk yamllint`, `rtk markdownlint`, `rtk hadolint`, `rtk pre-commit`, `rtk trunk`, `rtk sops`, `rtk systemctl`, `rtk brew`, `rtk ps`, `rtk iptables`, `rtk fail2ban-client`, `rtk quarto`, `rtk pio`, `rtk shopify`.

## Generic wrappers

```bash
rtk test <cmd>       # any test runner — failures only              -90%
rtk err <cmd>        # any command — errors only
rtk summary <cmd>    # heuristic summary of long output
rtk json f.json      # structure without values
rtk deps             # dependency summary
rtk env -f AWS       # env vars filtered by prefix
rtk log app.log      # deduplicated log lines
rtk proxy <cmd>      # raw passthrough, still tracked in analytics
```

## Not covered

Anything without a filter runs as passthrough — output reaches the model unchanged. `rtk discover` lists commands that ran raw but had an rtk equivalent available; `rtk proxy <cmd>` runs an unsupported command with usage tracking so it shows up in `rtk discover` as a gap.

## Analytics

```bash
rtk gain                        # summary stats
rtk gain --graph                # ASCII graph, last 30 days
rtk gain --history              # recent command history
rtk gain --daily                # day-by-day breakdown
rtk gain --all --format json    # JSON export
rtk discover                    # missed savings opportunities
rtk discover --all --since 7    # all projects, last 7 days
rtk session                     # rtk adoption across recent sessions
```

## Telemetry

Off by default, opt-in only (`rtk telemetry enable`). Collects aggregate counts and anonymized command names — never source, paths, arguments, or secrets. `rtk telemetry status | disable | forget`, or `RTK_TELEMETRY_DISABLED=1` to block regardless of consent.
