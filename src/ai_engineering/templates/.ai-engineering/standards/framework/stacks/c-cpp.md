# Framework C/C++ Stack Standards

## Update Metadata

- Rationale: establish C and C++ patterns for systems programming, embedded, and performance-critical applications.
- Expected gain: consistent memory safety, build management, and testing standards.
- Potential impact: C/C++ projects get enforceable safety, lint, and testing patterns.

## Stack Scope

- Primary languages: C17, C++20 (or later standard as adopted).
- Supporting formats: Markdown, JSON, YAML.
- Toolchain baseline: CMake 3.25+, GCC/Clang, Ninja (preferred build generator).
- Distribution: static/shared library, binary, container image.

## Required Tooling

- Build: CMake + Ninja (preferred), Make (fallback).
- Lint: `clang-tidy` (configured via `.clang-tidy`).
- Format: `clang-format` (configured via `.clang-format`).
- Static analysis: `cppcheck`, `clang-tidy`, address/thread/UB sanitizers.
- Test runner: GoogleTest (preferred), Catch2.
- Dependency vulnerability scan: `trivy` (container), manual dependency audit.
- Security SAST: `semgrep` (C/C++ rules), `gitleaks` (secret detection).

## Minimum Gate Set

- Pre-commit: `clang-format --dry-run -Werror`, `gitleaks`.
- Pre-push: `cppcheck`, `semgrep`, `cmake --build . && ctest`.

## Quality Baseline

- All public APIs documented with Doxygen-style comments.
- Test coverage target: per `standards/framework/quality/core.md`.
- Compiler warnings treated as errors (`-Werror` / `/WX`).
- Address sanitizer enabled in CI debug builds (`-fsanitize=address`).
- No raw `new`/`delete` in C++ — use smart pointers (`unique_ptr`, `shared_ptr`).

## Code Patterns

- **Error handling**: C: return codes with `errno`. C++: exceptions for exceptional cases, `std::expected` (C++23) or `Result<T,E>` pattern.
- **Memory safety**: C++: RAII, smart pointers, `std::span` for non-owning views. C: clear ownership conventions, paired alloc/free.
- **Concurrency**: `std::thread` + `std::mutex` (C++), `std::jthread` (C++20). pthreads (C). Prefer lock-free structures for hot paths.
- **Serialization**: `nlohmann/json` (C++), `cJSON` (C). Protocol Buffers for IPC.
- **Logging**: `spdlog` (C++). Custom lightweight logger (C).
- **Small focused functions**: <50 lines, single responsibility.
- **Project layout**: `src/`, `include/`, `tests/`, `cmake/`, `CMakeLists.txt`.

## Testing Patterns

- Unit tests: GoogleTest `TEST()` macros, Catch2 `TEST_CASE`.
- Integration tests: separate test binary per subsystem.
- Fuzzing: `libFuzzer` or AFL for security-critical parsers.
- Naming: `TEST(Module, Scenario_Expected)`.
- Fixtures: GoogleTest `::testing::Test` subclass.

## Update Contract

This file is framework-managed and may be updated by framework releases.
