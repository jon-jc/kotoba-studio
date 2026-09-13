# Agent Note: Subscription-agent workspace

Status: implemented

English | [中文](2026-09-12-subscription-agent-workspace.zh.md)

## Problem

Kotoba needs subscription coding agents, isolated task worktrees and review in one desktop workflow while retaining its full API Harness and bilingual voice tools. Orca's web account API is incomplete for desktop account management.

## Decision

Pin Orca 1.4.197 as a submodule and build its complete Electron interface and native services in a disposable checkout. Host the owned Windows window inside Qt. Agents becomes the primary workspace; API chat remains independently addressable. A user-restricted named pipe admits only project, navigation, snapshot and reviewed-draft operations. Verify both pipe-client PID and native-window PID against the owned QProcess, and require a per-launch reply nonce.

The selected local worktree updates code and voice context; busy voice work keeps its original root. Remote paths do not become local paths. Draft insertion requires a compatible empty native chat composer and never sends. The underlying CLI owns its permissions, authentication and subscription limits. Harness permissions remain separate and the Access button follows the active workspace.

The overlay isolates the profile, disables telemetry and the upstream local updater, removes duplicate tray/window controls, preserves normal CLI launch approval defaults, and applies Kotoba appearance and locale. Preserve upstream license files and runtime dependency resources. Packaging uses upstream probes for native PTY ownership, daemon loading, CLI resources and bundled plugins; publication occurs only after those pass.

## Alternatives considered

A separate Orca window would split the requested workflow. Its web client omits native account-management operations. Reimplementing its native agent launch, PTY and review code would duplicate a substantial existing implementation. A general JavaScript bridge would expose unnecessary authority; the fixed command vocabulary is sufficient for shared context and reviewed text.

## Consequences

The desktop contains two agent engines with different account and permission contracts. Subscription agents are primary, while API sessions retain independent history. The public README keeps English and Japanese in one file and is exempt from the inherited Chinese-pair requirement. Upstream submodules use their own lint toolchains.

## Verification and limits

Focused tests cover bundle path confinement, environment filtering, foreign replies/windows, stale context, draft rejection, primary navigation and busy-job workspace retention. A hidden Windows smoke boots the packaged native window, adds a disposable Git project, reads its selected worktree and rejects an unavailable draft. Paid provider turns, remote hosts, account setup and external publishing are not exercised. The embedded runtime currently targets Windows x64; signing, clean-machine qualification and broad external-service coverage remain separate release work.

## Embedded display correction (0.10.1)

Qt adopting the HWND did not update Electron's hidden-window compositor state. The fixed `present` operation reveals only an already-attached, visible workspace without activating it, disables renderer background throttling, and requests a compositor frame. A native Qt container reanchors the child at its own origin and nudges its size before fitting it, because Electron restores former top-level coordinates and can retain a stale surface. Hidden transitions are also sent to Electron. Showing Agents again repeats this handoff. Account navigation acknowledges success and reports failures; first-run onboarding yields to Settings without marking setup complete.

The hidden IPC smoke cannot validate composed pixels. `smoke_fleet_display.py` adds opt-in Windows Graphics Capture checks for a rendered workspace, account-page transition, resizing and hide/show restoration using an isolated profile and owned process cleanup. Its optional capture dependency is used only for verification; screenshots stay outside tracked documentation because detected account labels may be personal.

## Agent access and retired mobile companion (0.10.2)

The overlay replaces the global bypass switch with per-agent Plan, Ask and Workspace editing settings. Codex launch arguments configure its sandbox and escalation; Claude arguments configure native tool approval modes. OpenCode inline configuration sets global and built-in Plan/Build permission maps, retaining environment-file read protection and command approval. Unknown/custom configurations are identified instead of presented as enforced restrictions. Existing sessions and unsupported agents retain their own permission contracts. Exact legacy bypass presets migrate to manual defaults without overwriting custom arguments.

Mobile navigation, appearance entry, pairing IPC registration, desktop push startup and cloud relay startup are disabled in Kotoba. The pinned upstream source is unchanged. Focused tests cover policy mapping, conflicting arguments, configuration preservation and unsupported/custom states; native desktop checks cover settings navigation.
