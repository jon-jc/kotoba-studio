# Agent Note: LINE-first desktop messaging

Status: implemented

English | [中文](2026-09-12-line-first-messaging.zh.md)

## Problem

Kotoba needs a messaging entry point for English- and Japanese-speaking teams without making untrusted incoming messages automatic computer instructions. A connection form alone does not account for credential storage, incoming duplicates, conversation state, or ambiguous delivery.

## Decision

The native hub orders LINE, Slack, Discord, and Telegram and supports one saved connection per platform. An explicit gateway start owns a process lock, platform adapters, and an optional signed LINE HTTP receiver. Configuration edits take the same lock. Windows DPAPI protects credentials; schema-versioned SQLite stores text, drafts, aliases, unread watermarks and delivery state. The gateway stays alive in the tray and stops before application teardown. Notifications are opt-in and contain counts only.

LINE verifies the signature over the bounded raw request body and commits accepted, allowlisted messages before acknowledgement. Its public HTTPS ingress belongs to the user's tunnel or reverse proxy. Telegram uses long polling and refuses an existing webhook. Slack and Discord checkpoint new-message polling, including paginated catch-up; incoming history is ordered by provider time. Sender lists are mandatory, with additional group restrictions for LINE and Telegram. Bot messages are ignored when identified as such by the platform.

Only pressing Send queues a reply. Sending is recorded before the HTTP request, and acceptance after it. Crashes and timeouts during delivery leave uncertain rows that are never automatically resent. Interrupted queued rows become failed. Recovery restores text to a draft after confirmation. LINE carries a UUID retry key; Discord suppresses mentions and Slack sends literal text. API acceptance does not establish recipient delivery or reading.

AI reply preparation creates a reviewed request for the existing Voice agent route. Messaging turns use fresh, owned SDK sessions and close them on success or failure. The original Voice session is not reused. A proposed reply can be imported only into its originating conversation while its captured context still matches. Importing does not send. The no-tools instruction is a prompt request, not a new permission policy; the agent retains existing access controls.

The LINE setup tests a saved public receiver through the official webhook test API before an explicitly confirmed registration replaces the channel endpoint. Test-only mode does not mutate registration. Failed reachability blocks registration; webhook usage must be enabled separately in LINE Developers. No public address is provisioned by the registration API.

## Consequences

This is a Windows text messaging hub, not a replacement for full messaging clients. It does not synchronize attachments, voice, edits, deletions or reactions. Slack thread replies are excluded; Discord threads require their channel ID, and Telegram topics remain distinct. History is local plaintext; credentials are encrypted. Exports and handoffs contain at most the latest 200 local messages. Live platform-account behavior and model reply quality require separately configured credentials and are not established by fixture tests.

## Alternatives considered

Embedding the Hermes runtime would duplicate Kotoba's agent ownership and provider routing. The native adapters instead use each platform's published API while taking inspiration from Hermes's gateway setup, sender authorization and delivery ledger. Automatic remote agent execution would require a separately designed permission and approval flow. Silent retries of uncertain sends risk duplicate messages, so recovery requires explicit review.

## Verification

Tests cover Windows credential round trips, absent plaintext secrets, signature tampering, sender and group authorization, duplicate callbacks, durable acknowledgement, request size limits, outbox crash recovery, secret-free errors, pagination checkpoints, unread arrival tracking, exclusive gateway locks and future-schema refusal. A real loopback LINE receiver is started and stopped on an allocated port. Native tests cover LINE-first ordering, plain-text display, draft persistence, origin-bound AI reply imports and fresh SDK session cleanup. External sends use mock transports; native screenshots use fictional, unsent examples.
