        <!-- source: php overrides v1 (spec-133 D-133-12) -->

        # Php — Build Conventions

        Authoritative reference for the `ai-build` agent when generating
        php code.

        ## Toolchain

        - **Build / dependency**: Composer (`composer.json`)
        - **Lint / format**: stack-canonical linter (see `tdd_harness.md`)
        - **Type checker**: enabled where the stack supports it

        ## Patterns

        - PSR-12 coding style; ban camelCase for filenames.
- Laravel: prefer Eloquent over raw queries; sanitize all input via Request validation.
- Symfony: use DI container; never `new` in controllers.
