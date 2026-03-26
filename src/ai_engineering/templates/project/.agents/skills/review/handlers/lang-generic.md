# Handler: Language -- Generic

## Purpose

Generic language review handler for languages without a dedicated `lang-{language}.md` handler. Applies standards from the language's context file (`.ai-engineering/contexts/languages/{lang}.md`) to the diff.

## Integration

Dispatched as **Step 2b** (between Step 2 dispatch and Step 3 aggregate). Findings use the same YAML format. Language findings receive a **+10% confidence bonus** when corroborated by a concern agent.

## Procedure

### Step 1 -- Detect Language Scope

1. Map file extensions in the diff to language names:

   | Extensions | Language |
   |-----------|----------|
   | `.py` | python |
   | `.ts`, `.tsx` | typescript |
   | `.js`, `.jsx` | javascript |
   | `.go` | go |
   | `.rs` | rust |
   | `.cpp`, `.cc`, `.cxx`, `.hpp`, `.h` | cpp |
   | `.java` | java |
   | `.kt`, `.kts` | kotlin |
   | `.cs` | csharp |
   | `.swift` | swift |
   | `.dart` | dart |
   | `.php` | php |
   | `.sh`, `.bash` | bash |
   | `.sql` | sql |

2. Read `.ai-engineering/contexts/languages/{language}.md` for loaded standards
3. If no context file exists for the detected language, apply only the universal best practices from the concern agents in Step 2 -- do not produce lang-generic findings
4. Skip this handler entirely if all detected languages have a dedicated `lang-{language}.md` handler

### Step 2 -- Apply Context-File Standards

Check every changed line against the loaded language context file:

**Naming conventions** -- verify the diff follows the naming rules documented in the context file (casing, prefixes, suffixes, forbidden patterns).

**Idiomatic patterns** -- flag code that contradicts recommended patterns in the context file (e.g., using raw pointers where the context file says to use smart pointers).

**Anti-patterns** -- flag code that matches anti-patterns explicitly listed in the context file.

**Error handling** -- verify error handling follows the language's documented conventions.

**Testing** -- check that new code follows the testing patterns described in the context file.

### Step 3 -- Severity Mapping

| Severity | Criteria |
|----------|----------|
| critical | Security or memory safety issues flagged in the context file (buffer overflows, injection, unsafe deserialization) |
| major | Anti-patterns explicitly listed in the context file; missing error handling per documented conventions |
| minor | Style deviations from context file conventions; suboptimal patterns where the context file recommends a better alternative |

### Step 4 -- Diagnostic Tool Cross-Reference

If the language context file mentions specific tools, suggest running them:

| Language | Tool | Command |
|----------|------|---------|
| python | ruff | `ruff check {files}` |
| python | mypy | `mypy --strict {files}` |
| rust | clippy | `cargo clippy --all-targets -- -D warnings` |
| go | vet | `go vet ./...` |
| cpp | clang-tidy | `clang-tidy {files}` |
| typescript | tsc | `tsc --noEmit` |
| csharp | dotnet | `dotnet build --no-restore` |

If a diagnostic tool contradicts a finding, note the discrepancy and adjust confidence accordingly.

## Output Format

```yaml
findings:
  - id: lang-generic-N
    language: "{detected language}"
    severity: critical|major|minor
    confidence: 0-100
    file: path
    line: N
    finding: "description"
    evidence: "code snippet"
    context_rule: "Which section of {lang}.md this violates"
    remediation: "how to fix"
    self_challenge:
      counter: "why this might be wrong"
      resolution: "why it stands or adjustment"
      adjusted_confidence: N
```
