# Framework React Native Stack Standards

## Update Metadata

- Rationale: establish React Native patterns for mobile app development with cross-platform consistency.
- Expected gain: consistent mobile app quality, platform-specific handling, and testing patterns.
- Potential impact: React Native projects get enforceable patterns for iOS/Android development.

## Stack Scope

- Primary language: TypeScript (strict mode).
- Framework: React Native (Expo preferred, bare CLI when needed).
- Base standard: extends `standards/framework/stacks/typescript.md` — all TS rules apply.
- Supporting formats: JSON, Markdown.
- Toolchain baseline: inherits from TypeScript + RN-specific tooling.
- Distribution: App Store / Google Play, EAS Build, or internal distribution.

## Required Tooling

- Inherits all tooling from `typescript.md`.
- Build: Expo CLI (`npx expo`) or React Native CLI.
- Testing: Jest (`jest-expo` preset) + React Native Testing Library.
- E2E: Detox (preferred) or Maestro.
- Platform tools: Xcode (iOS), Android Studio (Android).

## Minimum Gate Set

- Pre-commit: inherits from `typescript.md`.
- Pre-push: inherits from `typescript.md` + `tsc --noEmit` with RN type definitions.

## Quality Baseline

- Inherits all quality rules from `typescript.md`.
- Platform handling: explicit `Platform.OS` checks or `.ios.ts`/`.android.ts` file extensions for platform-specific code.
- Accessibility: all touchable elements have `accessibilityLabel`. Use `accessibilityRole`, `accessibilityState`, `accessibilityHint` appropriately.
- Performance: avoid inline styles in FlatList items. Use `React.memo` for list items. Monitor re-renders with React DevTools Profiler.

## Code Patterns

- **Navigation**: React Navigation (stack, tab, drawer). Type-safe routes with `RootStackParamList`.
- **State management**: same as React standard — local first, Zustand/Jotai for global, TanStack Query for server state.
- **Styling**: StyleSheet.create for type-safe styles. Themed via context or design tokens. No inline style objects in render.
- **Native modules**: prefer Expo SDK modules. Use `expo-modules-api` for custom native code.
- **Offline first**: AsyncStorage for simple persistence. WatermelonDB or MMKV for complex data.
- **Deep linking**: configured via Expo linking or React Navigation deep link config.
- **Small focused components**: <100 JSX lines per component.
- **Project layout**: `src/screens/`, `src/components/`, `src/navigation/`, `src/hooks/`, `src/services/`.

## Testing Patterns

- Inherits patterns from `typescript.md`.
- Component tests: React Native Testing Library with `render`, `screen`, `fireEvent`.
- Platform-specific tests: separate test cases for iOS/Android behavior where platform code diverges.
- E2E: Detox flows for critical user journeys (auth, purchase, navigation).
- Snapshot tests: discouraged — prefer explicit assertions.

## Performance

_Stack-specific performance patterns will be added as the standard evolves. Refer to `review/performance/SKILL.md` for general performance review procedures._

## Security

_Stack-specific security patterns will be added as the standard evolves. Refer to `review/security/SKILL.md` for general security review procedures._

## Update Contract

This file is framework-managed and may be updated by framework releases.
