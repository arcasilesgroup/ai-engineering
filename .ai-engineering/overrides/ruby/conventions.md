        <!-- source: ruby overrides v1 (spec-133 D-133-12) -->

        # Ruby — Build Conventions

        Authoritative reference for the `ai-build` agent when generating
        ruby code.

        ## Toolchain

        - **Build / dependency**: Bundler (`Gemfile`)
        - **Lint / format**: stack-canonical linter (see `tdd_harness.md`)
        - **Type checker**: enabled where the stack supports it

        ## Patterns

        - Rubocop default profile + .rubocop.yml local overrides.
- Rails: prefer `where.not` over raw SQL; use scopes for query reuse.
- Never disable bundler-audit.
