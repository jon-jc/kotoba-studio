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

## Unified navigation (0.11.0)

A persistent left rail separates primary tools, collaboration and configuration. The desktop header contains only the current surface, project picker, command search and language. Hidden compatibility buttons retain the bridge contract while the duplicate Fleet action bar is removed. Remote-context and failure notices remain visible. The native runtime shares the desktop neutral palette and reduced-motion-aware transitions. Connections offers separate actions for subscription accounts, API providers and local models. Voice closes without destroying drafts; API navigation does not stop other sessions.

Focused desktop checks cover header geometry at 1024 pixels in English and Japanese, direct API navigation, retained voice drafts, account navigation from Code and project labels across locale changes. Windows Graphics Capture verifies the composed shell.

## Product cleanup (0.11.1)

Kotoba suppresses automatic and explicitly requested Orca CLI promotion tips. The Orca Account navigation, page and unexpected-signout promotion are removed; stale account links route to AI Provider Accounts, retaining coding-agent sign-in. The desktop introduction now describes bilingual voice, agent development and meeting handoffs. Voice selectors share aligned heights, padding and custom arrows. Focused promotion tests and the packaged access smoke cover the removed surfaces and retained account navigation.

## Sidebar and Windows Codex discovery (0.11.2)

The help menu omits upstream feedback, milestones, onboarding, documentation, changelog and social links. Its feedback dialog is no longer prefetched. Windows agent discovery includes valid executables in the desktop Codex version cache, preserving explicit PATH installs. Startup and Refresh append discovered directories so terminal launch and detection agree. Lookup is bounded, ignores incomplete downloads and does not execute binaries. Tests cover empty GUI PATH, updated installs, redirected LocalAppData, selection precedence and menu removal.


## Native keyboard and explicit agent chats (0.12.1)

The adopted Chromium child could have DOM focus while the outer Qt window retained Win32 keyboard focus. A trusted main-frame pointer gesture now requests a native focus handoff over the owned runtime's nonce-checked stdout. Qt revalidates the process owner, foreground root and child ancestry before `SetFocus`; background, hidden and detached windows cannot activate or receive focus. Tab focus into the native container follows the same handoff. No keys are synthesized by the application and polling never changes focus.

New supported chats use the pinned runtime's existing conversation transports. A one-time settings migration upgrades terminal-only defaults while preserving subsequent choices and existing sessions. **New chat** exposes Codex/Claude chat and terminal choices; each launch overrides only its local view preference, preserving account, permission arguments, workspace ownership and other conversations. Agents settings expose the default. Unsupported agents retain terminals; API chat remains separate.

Structured Codex initially fell back because Electron resolved an incomplete JavaScript-only native-module copy inside app.asar. The Windows process reader now resolves the validated resources/node_modules closure when hosted by Kotoba. It retains the compiled creation-time capability gate; no process-ownership proof is bypassed.

Verification includes native routing, migration, focus ownership and launch-mode tests plus an opt-in real Windows input smoke. The latter navigates the actual Agents project/Terminal 1 and Codex chat, executes a fixture shell command, retains an unsent draft across tab switches, opens model choices and restores the embedded window. Browser-injected keyboard events or a synthetic input field are not accepted as terminal-input proof. Paid agent turns, Japanese IME composition and unsupported provider chat transports remain outside this check.

The Windows host focuses Chromium’s renderer child only inside the owned foreground window, releases temporary UI-thread attachment, and defers Qt focus handoffs until activation finishes. Presentation explicitly shows the adopted surface after restore; the native keyboard smoke verifies shell execution, chat drafts, restored input, and the actual Codex terminal.


## Sidebar chat and Japanese catalog (0.12.2)

The left sidebar owns New chat. It targets the selected worktree, lists installed and enabled conversation adapters, retains explicit terminal choices, and opens project setup when no worktree is selected. Closing the menu without launching returns focus to its trigger. The tab toolbar no longer duplicates this entry.

An explicit Claude CLI authentication refusal opens an actionable sign-in notification instead of the generic structured-chat failure. Its action opens the Claude account section without replacing the selected project. Other errors preserve the existing ownership and reconciliation behavior. The user must complete Claude sign-in; the application does not substitute API credentials or bypass provider authentication.

The Japanese supplement completes the pinned English catalog and corrects short account and agent labels. Packaging rejects missing Japanese entries, unknown supplement keys and changed interpolation placeholders. Catalog merging preserves original nested and dotted keys and existing translations. English/Japanese UI switching does not translate user content, agent responses, commands or third-party product names.

Focused tests cover recovery classification, both languages, account navigation, selected worktrees, focus restoration and catalog validation. The packaged Windows smoke opens a disposable Git project, reproduces Claude refusal with an empty credential directory, follows Connect account, switches both languages and verifies project retention. It uses an isolated profile, atomically allocated debug port and owned process cleanup, with no global keyboard injection, sign-in or paid prompt. Live authenticated Claude responses remain unverified.

## Authenticated Claude startup (0.12.3)

A signed-in Claude CLI can complete SDK initialization without publishing a session-id-bearing startup event until the first user prompt. Waiting for that event before showing an empty composer times out. New Claude chats now use the existing terminal-backed conversation adapter; Codex retains structured transport. Account selection, permission arguments and runtime ownership remain on the existing launch path. The application neither synthesizes startup prompts nor fabricates session proofs.

Until Claude establishes its session, bilingual setup guidance replaces the composer and opens the underlying terminal for trust or sign-in. The user makes these choices in Claude and can return to Chat afterward. Real signed-in Windows tests delivered a short prompt through the composer, reopened the same profile, confirmed Claude in the restored terminal, and received another assistant reply through the chat Send button.

The parent now requests Electron's normal quit path over its owned local pipe. This allows renderer checkpoints and durable teardown before exit; forced cleanup is only a deadline fallback. The quit operation is not forwarded to page JavaScript. Tests cover valid quit requests, graceful and forced shutdown, launch routing and both setup languages. The credential-free packaged smoke verifies the first-run guide, terminal access and preserved project in English and Japanese.

## Claude language integration (0.12.4)

Claude Code's terminal menus are provider-owned English text. A Japanese terminal notice links to Kotoba's translated chat view while preserving the same session and terminal. The notice occupies its own layout row so terminal content and input remain unobstructed; switching to English removes it.

The owned parent pipe writes an atomic, language-only settings file inside the Kotoba runtime profile and passes its path to the renderer bridge. New local Windows Claude launches use that file with the supported settings flag. Custom settings arguments, other agents and remote targets are untouched; no global account settings or project files are modified. Older sessions need a new launch to attach the file. Tests cover language changes, path quoting, permission/model flag preservation, custom settings and target exclusions, plus the translated view button.

README screenshots show the 0.12.4 application in isolated demo profiles. The subscription-chat capture contains a real Claude response; API and voice drafts are unsent, collaboration examples are fictional, and voice/messaging gateways remain stopped. English and Japanese sections use matching captures; secondary setup views are expandable so the primary agent workflow stays prominent.
