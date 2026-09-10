# Agent Note: Desktop motion and recovery

Status: implemented

English | [中文](2026-09-10-desktop-motion.zh.md)

## Problem

Desktop transitions need continuity without delaying work, and recovery controls must remain usable after recording or settings failures.

## Decision

The [motion helper](../../../../python/voice/src/kotoba/motion.py) owns short opacity reveals on native voice and terminal panels. Hiding a panel cancels its animation and removes the temporary graphics effect. Chat receives scoped button transitions and popup fades through its existing desktop script integration. The saved Reduce motion preference disables these effects; Windows animation preferences and the browser reduced-motion media query are also respected. The initial web background matches the native shell.

The [voice controller](../../../../python/voice/src/kotoba/desktop.py) defers provider refresh during capture, clears unavailable provider displays without silently changing saved choices, and reports missing inputs or empty capture before inference. The [Access dialog](../../../../python/voice/src/kotoba/access_ui.py) exposes explicit reload after failures and disables controls that cannot act during a settings operation.

## Alternatives considered

Animating dock geometry would repeatedly resize editors and streaming chat. Permanent graphics effects add rendering work after transitions end. Automatic settings-write retries could apply a stale access choice after another client changed it; recovery therefore requires an explicit reload.

## Consequences

Controls remain immediately usable during reveals. Native motion is limited to owned panels, avoiding graphics effects on WebEngine. These transitions do not indicate inference progress or delay recording. Verification covers cancellation, reduced motion in the embedded browser, capture refresh, missing audio, provider removal, and settings recovery. The [Windows guide](../../../../python/voice/WINDOWS.md#motion-and-recovery) owns the user-facing controls.
