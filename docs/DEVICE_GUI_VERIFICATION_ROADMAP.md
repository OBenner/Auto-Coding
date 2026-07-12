# Device & GUI Verification Roadmap

Follow-up to the [Language Support Roadmap](LANGUAGE_SUPPORT_ROADMAP.md), which
brought detection, test discovery, security scanning, and CLI E2E verification
to parity across all 20 detected languages. Three verification targets were
explicitly left out of scope there: **mobile**, **embedded**, and **native
desktop GUI**. This document is the plan for closing them.

## The pattern

Every track below reuses the pipeline established by the first roadmap —
each slice is "same pipeline, new adapters":

1. **Detection** — recognize the target in `project/stack_detector.py` /
   `project/framework_detector.py`
2. **Allowlist** — add the toolchain binaries in
   `project/command_registry/`
3. **Test discovery** — add runner entries in
   `analysis/test_discovery.py` (`FRAMEWORK_PATTERNS`)
4. **MCP tooling** — give QA agents an interaction tool in
   `agents/tools_pkg/tools/` (precedents: Electron MCP for desktop web,
   `run_cli_session` for terminals)
5. **QA honesty** — prompts/reports state exactly what level of verification
   was achieved (unit / emulated / on-device / visual)

Verification levels, weakest to strongest — every slice must report which one
it delivers:

| Level | Meaning |
|-------|---------|
| L0 | Builds cleanly |
| L1 | Host-side unit tests pass |
| L2 | Runs in emulator/simulator, automated assertions pass |
| L3 | Screenshot verification (agent visually confirms UI state) |
| L4 | Scripted interaction (agent drives input and asserts responses) |
| L5 | On physical device/hardware (out of scope except serial harness) |

## Current state

| Target | Detection | Test discovery | Interaction | Best level today |
|--------|-----------|----------------|-------------|------------------|
| Android (Kotlin/Java) | ✅ #395 (`android`) | ❌ no instrumented-test entry | ❌ | L1 (JVM unit tests) |
| Flutter | ✅ | 🟡 `flutter test` (#388) | ❌ | L1 |
| iOS (Swift) | 🟡 `Package.swift` only, no Xcode project detection | 🟡 `swift test` (#388) | ❌ | L1 |
| React Native | ✅ (`react-native`) | 🟡 jest only | ❌ | L1 |
| Embedded (PlatformIO/Zephyr/ESP-IDF) | ❌ | ❌ | ❌ | L0 |
| Desktop GUI (Qt/GTK/native) | ✅ #395 (qt, gtest, …) | ✅ ctest (#388) | ❌ | L1 |
| Tauri | ✅ (`tauri`) | 🟡 jest/vitest only | ❌ | L1 |

## Track A — Android (highest value per effort)

Android is the most scriptable target: everything is CLI-driven through
Gradle and adb, no GUI automation frameworks needed.

### A1. Test discovery for instrumented tests

- `FRAMEWORK_PATTERNS` entries:
  - **Gradle Managed Virtual Devices** — detect `managedDevices` in
    `build.gradle(.kts)`; command `./gradlew <device>DebugAndroidTest`.
    Managed devices provision and tear down the emulator themselves — no
    lifecycle code on our side. Preferred path.
  - `connectedAndroidTest` as fallback when a device/emulator is already
    attached (guard: `adb devices` non-empty).
- Allowlist: `gradlew`/`adb` already present (#387/#395); add `emulator`,
  `avdmanager`, `sdkmanager`.
- **Exit criterion:** an Android project with managed devices gets a working
  L2 `test_command` from `TestDiscovery`.

### A2. adb interaction tools (computer-use for Android)

New MCP tools in `agents/tools_pkg/tools/` (QA agents only, mirroring
`run_cli_session`'s security posture):

- `android_screenshot` — `adb exec-out screencap -p`, compressed like
  Electron MCP screenshots (1MB SDK message limit)
- `android_input` — `adb shell input tap/swipe/text/keyevent`
- `android_logcat` — filtered `adb logcat -d` (analog of
  `read_electron_logs`)

The QA agent loop is then identical to the Electron one: screenshot → inspect
→ interact → verify. Delivers L3/L4.

### A3. Maestro flows (optional, higher level)

Detect `maestro/` or `.maestro/` flow dirs; allowlist `maestro`; test
discovery entry `maestro test`. YAML flows are LLM-friendly — the QA agent
can author a flow, run it, and keep it in the repo as a regression test.

## Track B — Flutter

- **B1.** Test discovery: `flutter drive` / `integration_test` entry when
  `integration_test/` exists; emulator lifecycle via
  `flutter emulators --launch <id>` (allowlist `flutter` already present).
- **B2.** Reuse Track A tooling: on Android targets the adb tools work
  unchanged; `flutter screenshot` covers attached devices generically.
- Widget tests already run headless (L1) via #388; B1 lifts Flutter to L2,
  B2 to L3/L4 on Android emulators.

## Track C — Embedded (emulation first, hardware never assumed)

The honest ceiling without hardware is L2 — and that is far better than the
current L0. Emulation makes firmware verification deterministic and CI-able.

### C1. Detection + allowlist + test discovery

| Ecosystem | Detect by | Test command | Notes |
|-----------|-----------|--------------|-------|
| PlatformIO | `platformio.ini` | `pio test -e native` | host-side L1; `pio test` on emulated envs where configured |
| Zephyr | `west.yml`, `prj.conf` | `west twister -p qemu_x86` (or configured qemu board) | QEMU targets built into twister |
| ESP-IDF | `idf.py`/`sdkconfig` | `idf.py build` + QEMU where available | weakest emulation story |
| Bare ARM | `arm-none-eabi-*` in Makefile/CMake toolchain | build-only | flag as L0, recommend Renode |

Allowlist additions: `pio`, `platformio`, `west`, `twister`,
`qemu-system-arm`, `qemu-system-riscv32`, `renode`, `arm-none-eabi-*`
(pattern), `openocd` (validator-gated).

### C2. Renode harness

Renode emulates whole SoCs/boards, is open-source, deterministic, and built
for CI. Slice: detect `.resc`/`.repl` scripts, allowlist `renode`, test
discovery entry `renode-test` (Robot Framework integration). Where a project
ships Renode scripts, QA gets scripted L2 firmware runs with UART assertions.

### C3. Serial harness (`run_serial_session`)

Mirror of `run_cli_session` over pyserial for users who *do* have a board
attached: open port, send scripted lines, assert expected substrings,
timeout. Same MCP-tool shape, same security posture (port allowlist via env,
e.g. `AUTO_CLAUDE_SERIAL_PORTS`). This is the only sanctioned L5 touchpoint.

### C4. QA honesty

QA prompts and `qa_report.md` must state the achieved level explicitly:
"verified in QEMU emulation; not tested on hardware". Never let an emulated
pass read as a hardware pass.

## Track D — Native desktop GUI (phased, screenshots first)

Full GUI driving is the most expensive item, so it is sliced by increasing
capability:

### D1. Launch + screenshot verification (L3)

New MCP tool `desktop_screenshot`: launch the built binary (security-
validated, project dir), wait, capture the app window:

- macOS: `screencapture -l <windowid>` (requires Screen Recording permission
  — must be documented as an explicit setup step)
- Windows: PowerShell `System.Drawing`/`Graphics.CopyFromScreen`
- Linux: `grim` (Wayland) / `import` (X11)

The QA agent is multimodal — "does the window show the expected dialog?" is
answerable from a screenshot alone. This one slice covers the majority of
"did the UI change land?" checks for Qt/GTK/wxWidgets/anything.

### D2. Accessibility tree read (structure without pixels)

Analog of Electron's `get_page_structure`, per platform:

- Windows: UIAutomation via `pywinauto` (most mature)
- Linux: AT-SPI (`pyatspi`)
- macOS: AXUIElement (weakest open tooling; requires Accessibility
  permission)

Platform adapters live in `core/platform/` per the cross-platform rules in
CLAUDE.md. Ship Windows first, Linux second, macOS last.

### D3. Input injection (L4)

Click/type/key tools completing the computer-use loop on top of D1+D2.
Coordinate-based input (cross-platform, works with D1 screenshots) before
element-based input (needs D2).

### D4. Tauri fast path

Tauri apps (detected since #395) are web-rendered — drive them via
`tauri-driver` (WebDriver) instead of D1–D3. Closer to the Electron/
Puppeteer path than to native GUI; can ship independently of D1–D3.

## Track E — iOS (last: macOS-only runners, most friction)

- **E1.** Detection: `*.xcodeproj`/`*.xcworkspace` (currently only
  `Package.swift` is detected); test discovery
  `xcodebuild test -destination 'platform=iOS Simulator,...'`; simulator
  lifecycle via `xcrun simctl boot/shutdown`. Gate everything on
  `is_macos()`.
- **E2.** Screenshots: `xcrun simctl io booted screenshot` — cheap L3.
- **E3.** Input injection needs `idb` (Meta) — evaluate before committing;
  Maestro (Track A3) also supports iOS and may be the cheaper L4 path.

## Suggested PR slicing

Priority order (impact per effort), each row one PR off `origin/develop`:

1. `feat(qa): Android instrumented test discovery (managed devices + connectedAndroidTest)` — A1
2. `feat(qa): adb interaction tools for QA agents (screenshot/input/logcat)` — A2
3. `feat(qa): embedded ecosystem detection + emulated test discovery (PlatformIO/Zephyr)` — C1
4. `feat(qa): run_serial_session harness over pyserial` — C3 (+ C4 prompt wording)
5. `feat(qa): flutter drive test discovery + emulator lifecycle` — B1 (B2 falls out of A2)
6. `feat(qa): desktop_screenshot launch-and-capture tool` — D1
7. `feat(qa): Renode harness for firmware verification` — C2
8. `feat(project): iOS Xcode project detection + simulator test discovery` — E1, E2
9. `feat(qa): Maestro flow support (Android + iOS)` — A3/E3
10. D2/D3 (accessibility tree + input) — schedule after D1 proves demand;
    Windows adapter first
11. `feat(qa): tauri-driver integration` — D4, independent

Every PR: fixture-based unit tests, multi-platform CI green, platform code
behind `core/platform/` abstractions, and QA reports stating the achieved
verification level (L0–L5).

## Non-goals

- Physical-device farms (Firebase Test Lab, BrowserStack) — external
  services with billing; revisit only on user demand.
- Hardware-in-the-loop beyond the serial harness (flashing, power control,
  logic analyzers).
- Commercial GUI automation (Squish, TestComplete).
