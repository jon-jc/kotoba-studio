# Agent Note: Parallel agent workbench

Status: implemented

English | [中文](2026-09-12-parallel-agent-workbench.zh.md)

## Problem

The desktop owns one browser client, so switching sessions replaces the visible conversation and makes independent drafts and provider activity difficult to follow. Multiple browser clients sharing selection storage would restore or overwrite the same selected session.

## Decision

A left-hand roster owns independent retained browser clients against the existing authenticated Harness host. One conversation is visible at a time. Each client uses a distinct persistent browser profile; the primary profile retains its existing path. Provider selection remains on the session's existing ModelDirectory, and agent execution remains on the existing loop. The desktop stores view IDs, names, selected session IDs, and child addresses without credentials or runtime URLs. A document-creation script restores selection across ephemeral loopback ports. Host-list readiness gates selection persistence.

The frame projects session ID, list readiness, and running state through desktop data attributes; the model seat exposes provider/model IDs. Native polling serializes these values as JSON and allows at most one pending read per view. A desktop navigation event replaces the web sidebar with the native roster; History & workspaces restores the existing sidebar, and Back to agents returns without reloading. Browser-only clients retain their normal layout.

Search, rename, keyboard switching, background completion reminders, and English/Japanese labels belong to the native roster. Switching views invalidates a pending voice paste. Closing a view requires confirmation, disposes its browser, and leaves admitted host work and saved sessions intact. Closing the application retains its existing runtime shutdown semantics.

## Alternatives considered

**Split conversations** were rejected by the user. **Independent replacement agent loops** would lose Harness tools, plugins, approvals, and durable event handling. **A shared browser profile for selection** would couple chats through storage. **One new host per view** would duplicate model processes and credential configuration without providing a required capability.

## Consequences

Retained browser clients consume memory per open agent. They share the configured host, credentials, tools, and filesystem permissions; a browser profile is not a security sandbox. Different workspaces remain necessary for conflicting file edits. A view can deliberately select an existing session from history, so two views may observe the same host agent. Tests cover simultaneous provider entry, independent cancellation and transcripts, native navigation and storage, child-address restoration, late callbacks, and the single visible conversation. Real desktop checks cover the composed Harness UI in both languages; provider tests use deterministic adapters without paid API calls.
