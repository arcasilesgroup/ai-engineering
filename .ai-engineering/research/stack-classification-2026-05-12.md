---
topic: Stack classification taxonomy — flutter, react-native, sql, java, php
date: 2026-05-12
tier: external-evidence
consumers: [spec-133 D-133-12, .ai-engineering/specs/spec.md]
---

# Stack Classification — Evidence for spec-133 Stack Expansion

## Comparative Taxonomy Across AI Frameworks

| Framework | Organizing Axis | Flutter/Dart | RN/TS | SQL | Evidence |
|---|---|---|---|---|---|
| **Cursor** (`.cursor/rules/*.mdc`) | Glob-driven, mix language + framework. `awesome-cursorrules` groups under "Mobile Development", "Database & API", "Language-Specific" | Standalone "Flutter Expert" stack | "React Native Expo" standalone stack | Embedded inside DB rules (Snowflake, etc.) | [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules), [cursor.directory](https://cursor.directory/) |
| **Continue.dev** | `.continue/rules/*.md` lexicographic; no taxonomy enforced | flat list | flat list | flat list | [Continue docs](https://docs.continue.dev/customize/deep-dives/rules) |
| **Aider** (`CONVENTIONS.md`) | Single flat conventions file + community repo organized **by framework, not language** | Has dedicated `flutter/` dir (no separate `dart/`) | none | none | [Aider-AI/conventions](https://github.com/Aider-AI/conventions) — dirs: `bash-scripts, flutter, functional-programming, golang, icalendar-events, moodle500, nextjs-ts` |
| **GitHub Copilot** | `.github/copilot-instructions.md` (single) + `.github/instructions/*.instructions.md` glob-scoped | path-pattern-scoped, no fixed taxonomy | same | same | [Copilot custom instructions](https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot) |
| **Flutter official** | Single combined ruleset for "Flutter and Dart" | **unified, not separated** | — | — | [Flutter AI rules](https://docs.flutter.dev/ai/ai-rules) |

**Key signal:** Industry pattern is **framework-as-stack**, not language-as-stack. Aider names dirs `flutter` and `nextjs-ts` (framework + language fusion). Flutter's own AI rules ship Dart + Flutter unified. Nobody ships standalone `dart/` rules with `flutter/` on top — the framework defines the conventions.

## Per-Stack Verdicts

| Proposed | Verdict | Justification |
|---|---|---|
| **java** | YES, independent T1 | Distinct toolchain (Maven/Gradle), JVM-specific security floor (Log4Shell, deserialization), idiomatic patterns (Spring beans, exceptions vs Result types) diverge sharply from Kotlin. Detection marker already in autodetect (`pom.xml`, `build.gradle`). High enterprise demand (banking/finance/regulated target audience). |
| **php** | YES, independent T2 | Distinct toolchain (Composer, PSR standards), security floor heavily PHP-specific (SQLi/XSS via PDO, `eval`, file uploads), Laravel/Symfony idioms. Detection marker (`composer.json`). Ubiquitous in legacy regulated systems. |
| **flutter** | INDEPENDENT stack (not extension of dart) | (1) Flutter's own official AI rules ship **combined** rather than split — proves framework owns conventions, not language ([Flutter AI rules](https://docs.flutter.dev/ai/ai-rules)). (2) Aider's community repo has `flutter/` with no separate `dart/`. Toolchain (`flutter test`, `flutter analyze`), widget idioms, state management (BLoC/Riverpod/Provider). Pure dart server projects rare → YAGNI on `dart/` bucket. |
| **react-native** | INDEPENDENT stack (not extension of typescript) | Distinct toolchain (Metro bundler, native modules, EAS Build), platform APIs (iOS/Android bridges), navigation patterns (React Navigation), state (Redux Toolkit/Zustand) all diverge from web React+TS. Aider uses framework-level naming (`nextjs-ts`); RN warrants same. Security floor differs (deep-link hijacking, OTA update signing). |
| **sql** | CROSS-CUTTING `_shared/sql.md`, NOT standalone stack | (1) SQL has no project-level marker analogous to `Cargo.toml` — ALWAYS coexists with host language. (2) Cursor community list embeds SQL inside DB-specific rules (Snowflake, Supabase), never standalone. (3) Repo already has `_shared/` — structurally consistent. Conventions ("parameterize", "use CTEs", "explain-plan large joins") are stack-agnostic and apply to Python+SQL, Java+SQL equally. Creating `overrides/sql/` would violate YAGNI (no detection trigger) and DRY. |

## Final Stack List (12 stacks + `_shared`)

| Stack | Tier | Marker |
|---|---|---|
| `python` | T1 | `pyproject.toml` |
| `typescript` | T1 | `tsconfig.json` |
| `go` | T1 | `go.mod` |
| `rust` | T1 | `Cargo.toml` |
| `java` | T1 NEW | `pom.xml` / `build.gradle` |
| `csharp` | T1 | `*.csproj` / `*.sln` |
| `kotlin` | T1 | `build.gradle.kts` |
| `swift` | T1 | `Package.swift` |
| `php` | T2 NEW | `composer.json` |
| `ruby` | T2 (marker exists, override NEW) | `Gemfile` |
| `flutter` | T2 NEW | `pubspec.yaml` + `flutter:` block (subsumes dart) |
| `react-native` | T2 NEW | `package.json` with `react-native` dep OR `app.json` Expo |
| `_shared/sql.md` | cross-cut NEW | not autodetected; cross-cuts host stacks |

**Excluded (YAGNI):** standalone dart, javascript (collapses to typescript), elixir.

## Disambiguation Rules

- **flutter vs dart-only:** if `pubspec.yaml` lacks `flutter:` block → emit dart-only signal (currently no override). If present → flutter stack.
- **react-native vs typescript:** RN takes precedence when marker present (`react-native` in deps OR `app.json` Expo OR `metro.config.js` OR `ios/`+`android/` dirs); else typescript.
- Document precedence order explicitly in `manifest.yml`.

## Sources

- [Cursor Rules Guide](https://www.vibecodingacademy.ai/blog/cursor-rules-complete-guide)
- [awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules)
- [Continue.dev Rules docs](https://docs.continue.dev/customize/deep-dives/rules)
- [Aider conventions repo](https://github.com/Aider-AI/conventions)
- [Aider conventions spec](https://aider.chat/docs/usage/conventions.html)
- [GitHub Copilot custom instructions](https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot)
- [Flutter AI rules (official unified)](https://docs.flutter.dev/ai/ai-rules)
- [evanca/flutter-ai-rules (community)](https://github.com/evanca/flutter-ai-rules)
- [Codingrules: React Native code style](https://www.codingrules.ai/rules/code-style-and-conventions-standards-for-react-native)
- [Modern SQL Style Guide](https://gist.github.com/mattmc3/38a85e6a4ca1093816c08d4815fbebfb)
- [Cursor Directory](https://cursor.directory/)
