# Agent Note: Desktop dictation and local meeting references

Status: implemented

English | [中文](2026-09-10-voice-workflows.zh.md)

## Problem

Short application recordings and in-window shortcuts did not support dictation into other desktop applications or durable meeting references. One multilingual default did not satisfy the separate English and Japanese requirements.

## Decision

[Voice Studio](../../../../python/voice/src/kotoba/desktop.py) uses an explicit processing mode and language-aware model selection. English selects Parakeet Unified through sherpa-onnx; Japanese selects the official Kotoba-Whisper v2 CTranslate2 conversion; automatic language detection selects multilingual Whisper Turbo. Local inference requires downloaded files and refuses incomplete tokenizers rather than allowing a hidden network fallback. Model downloads are explicit. Japanese uses segment timestamps because word alignment in the distilled model crashes the native runtime.

[Global dictation](../../../../python/voice/src/kotoba/global_dictation.py) adapts OpenWhispr's Windows paste behavior to Qt's native event filter. Registration is opt-in and disposed on exit. Delivery verifies the captured foreground window and process and refuses changed targets or held modifiers. It replaces the clipboard and never sends Enter. Uncertain results remain reviewable.

[Meeting capture](../../../../python/voice/src/kotoba/meetings.py) adapts OpenWhispr's session ownership and final-transcript persistence patterns. Capture callbacks feed bounded chunks; inference commits timestamped segments before reporting completion. Stop quiesces capture, drains queued chunks, and saves the tail. Overflow and source loss produce explicit incomplete records. Local SQLite provides notes, literal bilingual search, reviewed highlights, Markdown export, deletion, and interrupted-session recovery. Agent handoff creates a draft rather than executing transcript-derived actions.

## Alternatives considered

Embedding Electron's whole renderer inside the Qt desktop would duplicate application ownership, storage, and update infrastructure. The integration instead reuses native capture code, model definitions, and adapted lifecycle logic while preserving attribution. Automatic paste into a replacement foreground window and automatic cloud fallback would violate the selected destination and processing mode.

## Consequences

Windows global dictation and application capture are platform-specific. Source labels are not speaker diarization, keyword highlights are not generated summaries, and raw audio is not retained for crash recovery. Completed segments survive interruption; active and queued audio can be lost. Cloud speech is a separate explicit BYOK upload path. [The workflow guide](../../../../python/voice/VOICE.md) describes privacy boundaries, limits, and model choices; [evaluation records](../../../../python/voice/evaluation/README.md) distinguish caption agreement from verified accuracy.
