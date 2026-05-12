        <!-- source: react-native overrides v1 (spec-133 D-133-12) -->

        # React Native — Build Conventions

        Authoritative reference for the `ai-build` agent when generating
        react-native code.

        ## Toolchain

        - **Build / dependency**: Metro bundler + EAS Build / native build chain
        - **Lint / format**: stack-canonical linter (see `tdd_harness.md`)
        - **Type checker**: enabled where the stack supports it

        ## Patterns

        - Use Expo Router or React Navigation 7+; ban deprecated stack navigators.
- TypeScript strict mode; never `any`.
- Bundle analysis: react-native-bundle-visualizer in CI.
