# Agent Note: Embedded desktop workspace selection

Status: implemented

English | [中文](2026-09-10-desktop-workspace-picker.zh.md)

## Problem

A native folder chooser launched by the separate Harness process can open behind the Qt desktop window, leaving workspace selection apparently unresponsive. The collapsed sidebar also places the New Session glyph against its button's left edge instead of the shared icon center.

## Decision

The [desktop launch](../../../../python/voice/src/kotoba/workspace.py) supplies a [profile overlay](../../../../python/voice/assets/desktop-workspace.patch.yml) that disables the automatic directory picker and composes exactly one browse backend and one matching client interface. Both workspace entries use the existing folder browser, with Japanese strings supplied by the brand locale dictionary. The New Session control centers its glyph within the same 36-pixel button geometry as neighboring rail controls.

## Alternatives considered

Foreground activation of an independent Windows chooser depends on operating-system focus policy and still leaves an unowned dialog. A desktop-only folder action would bypass the workspace registration flow. Composing the browse interface alongside the automatic picker is invalid because both occupy the same single directory-flow slots.

## Consequences

Desktop folder selection remains inside the chat window and uses the shipped Harness workspace APIs. Browser and headless profiles launched independently retain their own configuration. The [Windows verifier](../../../../python/voice/verify_windows.py) exercises expanded and collapsed picker entry, measured icon centers, Japanese path adoption, and Japanese picker labels against the bundled executable. Picker unit tests continue to cover listing, cancellation, and errors. The [Windows guide](../../../../python/voice/WINDOWS.md#workspace-selection) owns user instructions.
