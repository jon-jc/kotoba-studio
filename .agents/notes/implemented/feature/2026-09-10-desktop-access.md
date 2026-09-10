# Agent Note: Desktop access selection

Status: implemented

English | [中文](2026-09-10-desktop-access.zh.md)

## Problem

Desktop users need a discoverable way to choose agent access without confusing a new-session default with the permission already recorded in an existing conversation.

## Decision

The [native Access dialog](../../../../python/voice/src/kotoba/access_ui.py) offers the shipped read-only, workspace-write, and danger-full-access presets. Its scope selector separates an individual chat from the default for new chats and the next voice conversation. Full access requires acknowledgment. [The controller](../../../../python/voice/src/kotoba/access.py) writes the revision-checked permission settings namespace for defaults and executes the existing audited permission command for live sessions. It reports success only after the backend accepts the operation. A default change closes the idle voice SDK client so a fresh conversation reads the saved policy.

## Alternatives considered

A desktop-only preference would diverge from the actual tool policy. Changing every conversation at once would silently widen authority for unrelated work. An automatic risk-review label is unsuitable because no machine approval reviewer is composed. The dialog describes the actual available enforcement instead.

## Consequences

Chat owns interactive approvals; the voice SDK fails closed when it cannot obtain approval. Windows confinement primarily restricts writes, with documented read, network, and filesystem limitations. Manual terminal commands and privileged plugins do not become confined by this selector. The dialog states these limits and blocks desktop dictation and application shutdown while it owns a settings operation. The [voice guide](../../../../python/voice/VOICE.md#agent-access) owns user instructions. Verification covers full-access acknowledgment, scope isolation, settings revision checks, live runtime permission changes, and the existing filesystem executor tests.
