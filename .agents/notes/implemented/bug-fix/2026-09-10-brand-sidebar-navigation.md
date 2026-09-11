# Agent Note: Brand button opens the workspace sidebar

Status: implemented

English | [中文](2026-09-10-brand-sidebar-navigation.zh.md)

## Problem

The workspace sidebar belongs to the embedded chat page and is hidden while native code or settings panels are selected. The desktop brand row offers no way to open it.

## Decision

The top-left icon and name form an accessible button that selects the retained chat page and expands its existing sidebar. The bridge uses the sidebar's localized accessible labels and only clicks the collapsed-state control. A bounded retry accommodates asynchronous startup; leaving chat stops further attempts. Code tabs, terminal output, and voice drafts remain owned by their existing panels.

## Alternatives considered

**Reloading the chat page** discards transient UI state and repeats startup. The button switches the existing page into view instead.

## Consequences

The sidebar is reachable from every native panel without creating a second navigation tree. The bridge depends on the existing sidebar accessible labels; desktop workflow tests and a real English/Japanese Code-to-sidebar check cover navigation and state preservation.
