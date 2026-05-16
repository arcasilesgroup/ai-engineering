# Swift — Security Floor

Minimum bar for `ai-build` output in Swift / iOS. Every control below
is mandatory; the agent escalates when it cannot meet a control.

## Input validation

- All external input (HTTP, deep link, intent) parsed via `Codable`
  with explicit struct definitions.
- Reject unknown fields; throw a typed error before the value
  reaches business logic.
- For URL parsing prefer `URLComponents` over string manipulation.

## Confidential storage

- Never store confidential values in `UserDefaults`.
- Use the iOS Keychain via Apple's APIs (or `KeychainAccess`,
  `SwiftKeychainWrapper` if a wrapper is preferred).
- For data at rest beyond Keychain (e.g. cached files), use
  `Data Protection` class A/B and explicit `NSFileProtection`.
- Never log raw confidential values, even at debug level.

## App Transport Security

- Default ATS on (`NSAllowsArbitraryLoads = false`).
- HTTPS-only outbound; no exceptions added to `Info.plist` without
  a specific business justification + sunset date.
- Pin certificates for high-value APIs via `URLSessionDelegate` if
  the threat model justifies it.

## Dependencies

- SwiftPM lockfile (`Package.resolved`) committed.
- Renovate / Dependabot configured to track CVEs.
- Audit transitives manually for unmaintained crates / abandoned
  GitHub repos.

## Privacy

- `NSPrivacyAccessedAPITypes` (PrivacyInfo.xcprivacy) declared for
  every restricted API the app uses (`UserDefaults`, file timestamp,
  disk space, system boot time).
- `App Tracking Transparency` prompt only when actually tracking.
- Localised purpose strings for camera, microphone, location, photos,
  contacts.

## Cryptography

- Use Apple's `CryptoKit` (`AES.GCM`, `Curve25519`, `SHA256`) — never
  roll your own.
- Hash login material with `argon2` (via swift-argon2) or PBKDF2 from
  CommonCrypto at strong iteration count.
- Random IDs: `SystemRandomNumberGenerator()`; never `arc4random`
  for security-relevant values.

## Memory & runtime

- Avoid retain cycles in closures: capture `[weak self]` (or
  `[unowned self]` only when you can prove the lifetime).
- Sanitise input lengths before passing to C / Objective-C bridges.
- `swift_arc_retain_check` and `Address Sanitizer` in CI for native
  code targets.

## Static analysis

- SwiftLint rules: `force_unwrapping`, `force_cast`,
  `force_try` raised to error level.
- Xcode static analyzer (`Build > Analyze`) for app targets.
- `gitleaks` or `trufflehog` on every PR.
