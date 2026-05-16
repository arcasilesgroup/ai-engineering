        <!-- source: flutter overrides v1 (spec-133 D-133-12) -->

        # Flutter — Build Conventions

        Authoritative reference for the `ai-build` agent when generating
        flutter code.

        ## Toolchain

        - **Build / dependency**: Flutter SDK (`pubspec.yaml` with `flutter:` block)
        - **Lint / format**: stack-canonical linter (see `tdd_harness.md`)
        - **Type checker**: enabled where the stack supports it

        ## Patterns

        - Use `BLoC` / `Riverpod` / `Provider` consistently — never mix.
- Const constructors everywhere possible (build performance).
- Run `flutter analyze` in CI; ban `lint: ignore_for_file` blanket suppressions.
