# Language Support Roadmap

Auto Code's pipeline (spec → planner → coder → QA loop) is language-agnostic, but the
*depth* of support varies sharply by language. This document maps the current state of
every language-related subsystem and defines a priority-ordered roadmap to bring all
detected languages to parity with Python/JavaScript.

## Status

**All five phases are COMPLETE.** The state matrix below is the original audit
snapshot, kept for historical context.

- **Phase 1 — DONE.** Detection bug fixes (#387); test discovery parity for
  JVM/.NET/native/scripting-tail ecosystems (#388).
- **Phase 2 — DONE.** SAST/dependency-audit runners for C/C++ (cppcheck), Go (gosec),
  Rust (cargo audit), PHP (composer audit) in #390; osv-scanner universal lockfile
  audit (Maven/Gradle, NuGet, Hex, SwiftPM, pub, Go modules) plus scanner/rules
  tables for all remaining languages in #394.
- **Phase 3 — DONE.** Framework detection for JVM (Spring Boot, Quarkus, Micronaut,
  Android, Compose), .NET (ASP.NET, MAUI, Unity), C/C++ (Qt, Boost, GTest, Catch2),
  Elixir (Phoenix, Ecto), and Swift (Vapor): #395.
- **Phase 4 — DONE.** Targeted test command templates + full test discovery in the
  project index (#402); ccache/sccache compiler-cache env for fresh worktrees (#412).
- **Phase 5 — DONE (CLI slice).** `run_cli_session` MCP tool: pseudo-terminal E2E
  harness for terminal applications, available to QA agents (#415). Native GUI,
  mobile, and embedded verification remain out of scope (see Phase 5 section).
- **Audit note:** `LANGUAGE_SECURITY_SCANNERS`/`LANGUAGE_SECURITY_RULES` in
  `security/language_rules.py` are a public API (`security/profile.py`) with no runtime
  consumers yet — actual scanning happens in `analysis/security_scanner.py`
  (used by the security auditor agent).

## Subsystems that define "language support"

| # | Subsystem | Location | Role |
|---|-----------|----------|------|
| 1 | Stack detection | `apps/backend/project/stack_detector.py` | Decides which languages a project uses |
| 2 | Command allowlist | `apps/backend/project/command_registry/languages.py` | Which binaries agents may run |
| 3 | Test discovery | `apps/backend/analysis/test_discovery.py` (`FRAMEWORK_PATTERNS`) | How QA finds & runs tests + coverage |
| 4 | Security scanners & rules | `apps/backend/security/language_rules.py` | Static analysis / dangerous-pattern review |
| 5 | Framework detection | `apps/backend/project/framework_detector.py` | Context for planner/coder prompts |
| 6 | E2E verification | Electron MCP / Puppeteer (`core/client.py`) | QA drives the running app |

## Current state matrix

Legend: ✅ full, 🟡 partial, ❌ missing, — not applicable.

| Language | 1. Detect | 2. Allowlist | 3. Test discovery | 4. Security rules | 5. Frameworks | 6. E2E |
|-----------|-----------|--------------|-------------------|-------------------|----------------|--------|
| Python | ✅ | ✅ | ✅ pytest, unittest | ✅ bandit/safety/semgrep | ✅ | 🟡 web only |
| JavaScript | ✅ | ✅ | ✅ jest/vitest/mocha/playwright/cypress | ✅ | ✅ | ✅ Electron/web |
| TypeScript | ✅ | ✅ | ✅ (via JS) | ✅ | ✅ | ✅ Electron/web |
| Rust | ✅ | ✅ rich (cargo-*) | ✅ cargo test + tarpaulin | ✅ | ✅ web frameworks | ❌ |
| Go | ✅ | ✅ | ✅ go test + cover | ✅ | ✅ web frameworks | ❌ |
| Ruby | ✅ | ✅ | ✅ rspec/minitest | ✅ | ✅ | ❌ |
| PHP | ✅ | 🟡 no phpunit binary | ❌ (phpunit detected as framework but no runner entry) | ✅ | ✅ | ❌ |
| Java | 🟡 misses `build.gradle.kts` | ✅ mvn/gradle | ❌ no JUnit/mvn test/gradle test | ❌ | ❌ | ❌ |
| Kotlin | 🟡 `*.kt` only | 🟡 no gradle in `kotlin` set | ❌ | ❌ | ❌ | ❌ |
| Scala | ✅ | ✅ sbt | ❌ no sbt test | ❌ | ❌ | ❌ |
| C# | ✅ | ✅ dotnet | ❌ no dotnet test | ❌ | ❌ | ❌ |
| C | ✅ | 🟡 no ctest/ccache/debuggers | ❌ | ❌ | ❌ | ❌ |
| C++ | ✅ | 🟡 same as C | ❌ no ctest/gtest/catch2 | ❌ | ❌ | ❌ |
| Elixir | ✅ | ✅ mix | ❌ no mix test | ❌ | ❌ no Phoenix | ❌ |
| Swift | ✅ | ✅ | ❌ no swift test | ❌ | ❌ | ❌ |
| Dart/Flutter | ✅ | ✅ | ❌ no dart/flutter test | ❌ | ✅ | ❌ |
| Haskell | ❌ not detected | ✅ (dead entry) | ❌ | ❌ | ❌ | ❌ |
| Lua | ❌ not detected | ✅ (dead entry) | ❌ | ❌ | ❌ | ❌ |
| Perl | ❌ not detected | ✅ (dead entry) | ❌ | ❌ | ❌ | ❌ |
| Zig | ❌ not detected | ✅ (dead entry) | ❌ | ❌ | ❌ | ❌ |

### Known bugs found during this audit

- **Kotlin-only Gradle projects get no build tool.** `stack_detector.py` detects Java via
  `pom.xml` / `build.gradle` / `*.java` but not `build.gradle.kts` / `settings.gradle.kts`,
  and the `kotlin` allowlist set lacks `gradle`/`gradlew`. A modern Kotlin project
  (Android or backend) therefore cannot run its own build.
- **Dead allowlist entries.** `LANGUAGE_COMMANDS` defines `haskell`, `lua`, `perl`, `zig`,
  but `stack_detector.detect_languages()` never emits those keys, so the commands are
  unreachable.
- **PHPUnit is detected but not runnable.** `framework_detector.py` reports `phpunit`,
  but `FRAMEWORK_PATTERNS` has no entry for it and the `php` allowlist has no
  `phpunit` binary (only `php`, `composer`).

## Roadmap

Ordering is by impact-per-effort, not by calendar. Each phase is sized to be one or a
few focused PRs against `develop`, each independently shippable and testable.

### Phase 1 — Test discovery parity (highest impact, low effort)

The QA loop is only as good as its ability to run tests. Every entry below is a
mechanical addition to `FRAMEWORK_PATTERNS` in `analysis/test_discovery.py`, plus the
matching binaries in `command_registry/languages.py`.

| Language | Detection signal | `command` | `coverage_command` | New allowlist binaries |
|----------|------------------|-----------|--------------------|------------------------|
| Java (Maven) | `pom.xml` | `mvn test` | `mvn verify` (jacoco) | — (mvn present) |
| Java/Kotlin (Gradle) | `build.gradle(.kts)` | `./gradlew test` | `./gradlew jacocoTestReport` | add `gradle`,`gradlew` to `kotlin` |
| C# | `*.csproj`/`*.sln` | `dotnet test` | `dotnet test --collect:"XPlat Code Coverage"` | — |
| C/C++ (CMake) | `CMakeLists.txt` + `enable_testing`/`add_test` | `ctest --test-dir build --output-on-failure` | `gcovr` | `ctest`, `gcovr`, `ccache` |
| C/C++ (Make) | `Makefile` with `test:` target | `make test` | — | — |
| PHP | `phpunit.xml(.dist)` or composer dep | `vendor/bin/phpunit` | `vendor/bin/phpunit --coverage-text` | `phpunit` |
| Elixir | `mix.exs` | `mix test` | `mix test --cover` | — |
| Swift | `Package.swift` | `swift test` | `swift test --enable-code-coverage` | — |
| Dart | `pubspec.yaml` | `dart test` / `flutter test` | `flutter test --coverage` | — |
| Scala | `build.sbt` | `sbt test` | `sbt coverage test` | — |
| Zig | `build.zig` | `zig build test` | — | — |
| Haskell | `*.cabal`/`stack.yaml` | `cabal test` / `stack test` | — | — |

Also in this phase (small, same-area fixes):

- Fix Kotlin/Gradle detection (`build.gradle.kts`, `settings.gradle.kts`) in
  `stack_detector.py`.
- Add detection for the four dead languages (`*.hs`+`*.cabal`, `*.lua`+`.luarocks`,
  `*.pl`+`cpanfile`, `*.zig`+`build.zig`) so their allowlist entries become live.
- Tests: extend the existing detector unit tests with one fixture project per new
  framework entry.

**Exit criterion:** for every language in the matrix, a project with a standard test
setup gets a working `test_command` from `TestDiscovery` without manual configuration.

### Phase 2 — Security scanners & rules parity

Extend `LANGUAGE_SECURITY_SCANNERS` and `LANGUAGE_SECURITY_RULES` in
`security/language_rules.py`, and allowlist the scanner binaries. Priority order within
the phase reflects how dangerous the *absence* of scanning is:

1. **C/C++** (memory safety is invisible to the current QA loop):
   - Scanners: `clang-tidy`, `cppcheck`, `flawfinder`; allowlist `valgrind`.
   - Rules: `strcpy/sprintf/gets/system/malloc-without-check` as dangerous functions;
     recommend sanitizer builds (`-fsanitize=address,undefined`) in secure_alternatives.
   - QA prompt addendum: when stack includes c/cpp, instruct the QA reviewer to run the
     test suite under ASan/UBSan when a sanitizer build target exists.
2. **Java/Kotlin**: `spotbugs`, `semgrep`, `detekt` (Kotlin); rules for
   `Runtime.exec`, XXE-prone XML parsers, `ObjectInputStream` deserialization.
3. **C#**: `security-scan` (Security Code Scan), `dotnet list package --vulnerable`;
   rules for `BinaryFormatter`, SQL string concatenation, `Process.Start`.
4. **Elixir**: `sobelow`, `credo`; rules for `Code.eval_string`, `:os.cmd`.
5. **Swift/Dart/Scala**: `swiftlint`, `dart analyze`, `scalafix` as lint-level scanners.

**Exit criterion:** `LANGUAGE_SECURITY_SCANNERS` has an entry for every detectable
language, and the security auditor prompt references the per-language rules.

### Phase 3 — Framework detection & context quality

Planner/coder context currently understands web frameworks for scripting languages
only. Extend `framework_detector.py`:

- **Java/Kotlin**: Spring Boot (`spring-boot` in pom/gradle), Quarkus, Micronaut,
  Android (`com.android` plugin).
- **C#**: ASP.NET Core (`Microsoft.AspNetCore`), MAUI, Unity (`ProjectVersion.txt`).
- **C/C++**: Qt (`find_package(Qt...)`), Boost, gtest/catch2 presence (feeds Phase 1
  detection), embedded toolchains (`arm-none-eabi` in CMake toolchain files — used to
  *warn* that verification will be build-only).
- **Elixir**: Phoenix (`phoenix` in mix.exs).
- **Swift**: Vapor, SwiftUI vs UIKit.

This phase is prompt-visible only (no security surface), so it can proceed in parallel
with Phase 2.

**Exit criterion:** for each supported language, at least the dominant application
framework is reflected in the planner/coder context.

### Phase 4 — QA iteration economics for compiled languages

Compiled stacks make the coder → QA → fixer loop expensive. Reduce per-iteration cost:

- Allowlist and document `ccache`/`sccache`; prime them in the worktree setup step
  (`cli/worktree.py`) so fresh worktrees don't cold-build.
- Teach the QA fixer to run *targeted* tests first (single test binary / `ctest -R` /
  `gradle test --tests`) before full suites — extend `test_discovery` entries with an
  optional `targeted_command` template.
- Add debugger binaries (`gdb`, `lldb`) behind a validator that restricts them to the
  project directory (extend `security/process_validators.py`).

**Exit criterion:** a C++/Java QA-fix iteration reuses the previous build and runs only
affected tests by default.

### Phase 5 — Verification beyond web/Electron (research track)

E2E today = Electron MCP + Puppeteer. Options, in rough order of feasibility:

1. **CLI apps (any language)**: lowest-hanging fruit — a pseudo-terminal harness
   (spawn app, feed stdin, assert on stdout) would cover most C/Go/Rust tools. No new
   MCP server needed; can be a QA-prompt pattern plus an allowlisted helper.
2. **Native desktop GUI**: platform accessibility APIs (AXUIElement on macOS,
   UIAutomation on Windows, AT-SPI on Linux) via a new MCP server. Large effort;
   evaluate existing MCP servers before building.
3. **Mobile (Flutter/Swift/Kotlin)**: emulator + `flutter drive` / XCUITest /
   Espresso. Requires emulator lifecycle management inside the sandbox — treat as
   out of scope until 1–2 land.
4. **Embedded**: hardware-in-the-loop is out of scope; the honest posture is what
   Phase 3 adds — detect embedded toolchains and explicitly downgrade QA claims to
   "builds + host-side unit tests pass".

## Suggested PR slicing

Each row is one PR off `origin/develop` (per repo contribution rules):

1. `fix(project): detect Kotlin/Gradle kts + dead languages (haskell/lua/perl/zig)` — bug fixes, no new surface.
2. `feat(qa): test discovery for JVM + .NET (mvn/gradle/dotnet/sbt)` — Phase 1, part 1.
3. `feat(qa): test discovery for native + scripting tail (ctest/make/phpunit/mix/swift/dart/zig/haskell)` — Phase 1, part 2.
4. `feat(security): C/C++ scanners and rules + sanitizer guidance` — Phase 2, item 1.
5. `feat(security): JVM/.NET/Elixir/Swift scanner rules` — Phase 2, items 2–5.
6. `feat(project): framework detection for JVM/.NET/C++/Elixir/Swift` — Phase 3.
7. `feat(qa): build caching + targeted test runs for compiled stacks` — Phase 4.
8. Phase 5 items individually, starting with the CLI harness.

Every PR must include unit tests with fixture projects (see existing patterns in
`tests/`) and pass multi-platform CI — compiler/tool names differ on Windows
(`cl.exe`, `gradlew.bat`), so allowlist additions must go through the platform
abstraction in `apps/backend/core/platform/` where paths are involved.
