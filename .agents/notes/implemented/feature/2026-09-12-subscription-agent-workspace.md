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
