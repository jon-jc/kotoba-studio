# Agent Note: Native voice conversations

Status: implemented

English | [中文](2026-09-13-native-voice-conversations.zh.md)

## Problem

Dictation and operating-system text-to-speech do not provide a shared native audio conversation. Kotoba needs spoken and typed turns together without granting an audio model silent computer access.

## Decision

The Python desktop owns one explicitly started voice connection. Provider adapters implement OpenAI Realtime, Gemini Live, and Grok Voice. A bounded worker exchanges PCM audio and normalized transcript events; the existing Harness and subscription agents keep their own execution and permission models. Reviewed text enters their draft handoff without submission. Raw audio is ephemeral and is never replayed or persisted as a Harness session.

Push-to-talk is the default. Hands-free uses server speech detection with an initially muted microphone. Closing the panel or application stops the connection, and shutdown waits for worker completion. Calls have a 30-minute cap, bounded setup and close timeouts, bounded input/output queues, and no automatic retry or provider fallback. Windows WASAPI can use the system format converter. Headphones are recommended because acoustic echo cancellation is absent.

The voice panel accepts a session-only key, an explicitly saved Windows DPAPI key, or its provider's environment variable in that precedence order. It does not add a secret-reading RPC to the Harness credential controller. Provider changes clear the input key. Errors expose fixed categories rather than URLs, headers, or provider payloads. Typed prompts and audio share a provider session; Gemini uses realtime input for ongoing text because its current model reserves client content for initial history.

## Alternatives considered

Composing local transcription with text generation and speech synthesis would retain wider provider coverage but would not provide native speech-to-speech behavior. Exposing saved Harness secrets over RPC would weaken its existing one-way credential boundary. Reusing subscription-agent sign-in would imply voice API access those accounts do not grant.

## Consequences

Voice API credentials have a distinct setup step. Voice models cannot act on files or tools; the user reviews and sends actionable text through the chosen agent. OpenAI and Grok interruption clears playback and truncates unheard audio in server context. Gemini playback stop does not cancel server generation; speaking or typing provides the next native interruption. Transcripts remain in memory until a new call or app exit, with a 200-entry bound. Switching language preserves the live widget through QScrollArea.takeWidget so two scroll areas never own it concurrently.

## Verification and limits

Keyless tests exercise all three wire adapters, final transcript replacement, microphone gating, bounded playback, sanitized errors, fake transport setup and teardown, provider-scoped keys, review handoff, hide-to-stop behavior, and visible locale rebuilds. A native Windows preview verifies the panel layout. Paid provider turns, account entitlements, headset acoustics and clean-machine audio compatibility are not established by these tests. The user guide documents those limits and the distinction between live cloud voice and local dictation.
