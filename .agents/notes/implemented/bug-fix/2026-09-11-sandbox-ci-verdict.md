# Agent Note: Sandbox CI verdict

Status: implemented

English | [中文](2026-09-11-sandbox-ci-verdict.zh.md)

## Problem

The macOS parity suite rejects the onboarding provider selector's 1px neutral border. Sandbox shell steps disable automatic exit and can replace a failed test command's status with a successful summary match.

## Decision

The selector uses the theme's 0.5px neutral border. Both sandbox steps explicitly exit with a failed command's status before checking the summary. Successful commands must still report all expected files without skips. Focused theme and shell-verdict regressions also run in the voice pull-request job. The [master-only sandbox matrix](../process/2026-07-21-serial-cross-platform-ci-reference.md) remains enabled.

The documentation image-escape fixture links an outside directory with a junction on Windows and a directory symlink on POSIX. This preserves real-path escape rejection without requiring Windows file-symlink privileges.

## Alternatives considered

**Removing the macOS check** hides a reproducible styling defect and loses platform coverage. **Trusting only the summary** can accept a command that reports passing files but fails during teardown.

## Consequences

The shell regression executes both workflow scripts with controlled command results, including nonzero exit status paired with a passing summary and zero exit status paired with skipped files. It uses Bash on Linux/macOS and Git Bash where installed on Windows; hosted Linux provides the required pull-request evidence. Real confinement remains verified by the unchanged kernel matrix after merge.
