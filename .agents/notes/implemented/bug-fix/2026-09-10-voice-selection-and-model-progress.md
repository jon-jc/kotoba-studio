# Agent Note: Voice selection and model setup feedback

Status: implemented

English | [中文](2026-09-10-voice-selection-and-model-progress.zh.md)

## Problem

Wheel input changes voice tabs and model selections while users scroll. Large speech downloads give no indication of transfer or loading progress.

## Decision

Native voice tab bars and closed dropdowns ignore wheel input while preserving click and keyboard selection. Model setup reports per-operation progress through queued Qt signals. Parakeet reports archive bytes before checksum verification and extraction; Whisper uses the pinned faster-whisper registry and Hugging Face snapshot callback. Unknown totals remain indeterminate. The interface reports completion only after loading succeeds and clears progress on failure.

The root product README retains its English/Japanese navigation. Its Chinese counterpart remains checked for content consistency without requiring a Chinese switcher on the product landing page; other authored documentation keeps the existing switcher requirement.

## Alternatives considered

**Estimated time-based percentages** misrepresent slow downloads and model loading. Progress uses measured bytes or file counts instead.

**Global download hooks** affect concurrent library callers. A callback class belongs to each snapshot operation instead.

## Consequences

Users can scroll without changing agent configuration and distinguish downloads from local loading. Existing cache, offline, and checksum rules remain in effect. Hugging Face versions that expose only file progress show file counts; setup does not promise a remaining-time estimate. Focused tests cover wheel input, keyboard selection, byte reporting, unknown totals, queued UI updates, and failure recovery.
