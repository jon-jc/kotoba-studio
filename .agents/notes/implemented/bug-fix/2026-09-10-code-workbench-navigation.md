# Agent Note: Code workbench navigation

Status: implemented

English | [中文](2026-09-10-code-workbench-navigation.zh.md)

## Problem

The selected Code button cannot dismiss its page. The empty viewer shows unused search controls and provides little separation between workspace navigation and file content.

## Decision

Code toggles back to chat and exposes a localized close action. Escape dismisses search before leaving Code; Ctrl+W closes a file or leaves the empty page. Switching pages preserves open files. Explorer, workspace-relative paths, source tabs, and compact status occupy separate areas. Search remains hidden until requested and is unavailable without a file. The empty state offers folder selection. Existing read-only, UTF-8, size-limit, and syntax-highlighting behavior remains in effect.

## Alternatives considered

**Discarding tabs on close** makes navigation destructive and forces users to reopen their working context. Closing the Code page only changes the selected panel.

## Consequences

Users can leave Code using the toolbar or keyboard and return to the same files. File closure still releases its editor. Native workflow tests cover navigation, retained tabs, search dismissal, and the final-tab empty state; visual checks cover both languages and keyboard actions.
