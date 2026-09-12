# Agent Note: Configured providers and per-chat model controls

Status: implemented

English | [中文](2026-09-12-configured-provider-selectors.zh.md)

## Problem

Registration order placed DeepSeek ahead of providers with saved credentials. One combined model menu made selecting a provider harder, and the native voice directory treated every registered route as configured.

## Decision

The host catalog adds optional `configured` metadata by inspecting the provider’s resolved settings and credential description. Only availability crosses the client boundary. Missing credential services or failed credential descriptions leave readiness unknown. Keyless profiles are usable; absent profiles are unconfigured. Stable sorting puts configured groups first. The settings controller uses its existing credential readiness predicate for the same ordering.

Each chat has separate provider and model controls. Changing provider selects its first advertised model through the existing session selection command; the model menu contains only that provider’s models. Reasoning effort remains model-owned. A directory load can replace an unconfigured deployment default only when neither a prior request nor an explicit session selection exists, and no newer selection or connection generation has intervened. Existing chats retain their selections. Native voice follows the catalog readiness and falls back to a configured provider without carrying a different provider’s model ID.

## Verification

Host tests cover saved custom key references, refresh, and credential lookup failure. Client tests cover provider ordering, filtered model choices, reasoning effort, failed selection, and independent session choices. Native tests cover configured-provider fallback and preservation of custom model IDs. No external model request is needed for these controls.

## Consequences

A configured badge means credentials are present, not that a remote service has accepted them. Unknown readiness remains selectable. Provider catalog failures remain visible with retry. Sorting is stable and never changes an existing session selection merely because another key is saved.

## Alternatives considered

Hardcoding OpenAI first would replace one vendor preference with another and ignore custom gateways. Sorting by adapter registration alone cannot distinguish saved credentials. A single mixed model menu requires scanning unrelated providers, so the composer separates provider and model selection while retaining the existing session controller.
