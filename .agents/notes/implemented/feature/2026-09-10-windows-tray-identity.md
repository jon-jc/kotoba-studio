# Agent Note: Windows tray lifecycle and application identity

Status: implemented

English | [中文](2026-09-10-windows-tray-identity.zh.md)

## Problem

Windows can group source-launched windows under Python without an explicit application identity. Closing the desktop also terminates a workspace that the user wants to keep available in the background.

## Decision

Kotoba sets `KotobaStudio.Desktop` before creating Qt UI; installed shortcuts carry the same identity and explicitly reference the bundled Kotoba icon. The application-wide icon also covers native dialogs and the system tray.

When a tray is available, closing the main window hides it while retaining the runtime and workspace state. The localized tray menu restores the window, opens Voice Studio, or quits. Quit follows the existing process cleanup path. Active native recording or processing rejects close and quit and restores the window. If the tray becomes unavailable, closing exits rather than leaving an inaccessible background app.

## Alternatives considered

**Keep Windows' inferred identity.** An embedded executable icon alone does not give source launches a distinct taskbar group. A shared explicit identity keeps process and shortcut grouping consistent.

**Always hide on close.** A missing tray would leave the application without a restore control. The close behavior therefore checks availability at the time of closing.

## Consequences

Users explicitly quit through the tray menu. No sign-in startup entry is created. Existing Python pins may require re-pinning the installed Kotoba shortcut. Native workflow tests cover preservation, restoration, localization, active-capture rejection, tray loss, and cleanup; packaged verification can require the real Windows tray with `--tray`.
