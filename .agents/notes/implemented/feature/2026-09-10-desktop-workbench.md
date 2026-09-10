# Agent Note: A conversation-first desktop workbench

Status: implemented

English | [中文](2026-09-10-desktop-workbench.zh.md)

## Problem

Permanent navigation rails and voice configuration compete with the current task. Copying a transcript and locating the chat input adds a manual step, while a single file viewer loses context when comparing source files.

## Decision

The native shell uses one compact toolbar, an optional voice dock, and a bottom terminal. Routing, plugins, and local models remain available through the overflow menu and command palette. The embedded conversation retains ownership of sessions, credentials, model selection, and agent execution.

Reviewed voice text enters the visible editable composer through Qt's native paste action, preserving the existing draft and never submitting it. An unavailable composer leaves the reviewed text on the clipboard. Each asynchronous handoff identifies its request so an older completion cannot paste a newer clipboard value. Source files use read-only tabs with line numbers and wrapping search; unreadable, binary, and oversized files leave open tabs intact.

## Alternatives considered

**Keep both navigation rails.** Duplicate permanent navigation consumes horizontal room and makes the voice panel compete with the task. The compact toolbar retains the same destinations without a second sidebar.

**Replace the embedded chat.** Reimplementing the conversation would split ownership of plugins, sessions, approvals, and model routes. The native shell supports the complete existing chat instead.

**Write directly into editor state.** Private editor state would couple the desktop to the composer implementation. Native paste follows the editor's normal input path and preserves its review-before-send behavior.

## Consequences

Code tabs preserve reading context but do not edit files or reload changed files automatically. Source edits and diffs remain in the agent workspace. The voice handoff uses the system clipboard; it falls back to copying when no conversation is editable. Native tests exercise draft preservation, source navigation, language switching, and the no-submit behavior; embedded-browser checks cover the actual composed editor.
