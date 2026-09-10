# Agent Note: Provider-neutral onboarding

Status: implemented

English | [中文](2026-09-10-provider-neutral-onboarding.zh.md)

## Problem

The first-run credential dialog directs every new user to DeepSeek even though the installed multi-provider adapter supports other native APIs. Saving only a credential does not activate a dormant provider route.

## Decision

The onboarding selector uses the shared configurable-provider directory, preferring OpenAI, Anthropic Claude, Kimi through Moonshot AI, and DeepSeek. The installed adapters supply protocols, endpoints, and model catalogs. OpenAI uses Responses, Anthropic uses Messages, and Moonshot uses Chat Completions. Custom gateways remain configurable from Models. Claude API keys are distinct from a Claude Code subscription or CLI login.

The credential editor writes a dormant catalog route's credential reference before storing its key. Successful settings writes enter the shared mirror before readiness refreshes. A failed credential write leaves the editor available for retry; it never reports a working provider based on key persistence alone. Switching providers remounts the editor and clears an unsaved key. Saving disables the selector. Existing usable routes bypass setup, and Configure later permits local-model setup.

## Alternatives considered

**A second provider implementation.** Reusing the installed native SDK adapters preserves streaming, tool replay, model capabilities, and the existing credential architecture without maintaining duplicate transports.

**Changing only the introductory text.** Provider selection must activate the corresponding route, or the model picker still cannot offer its models.

## Consequences

English, Japanese, and Chinese setup copy describes the same workflow. Tests exercise isolated credentials, route activation without DeepSeek, switching, pending writes, and native protocol tool streams with Japanese arguments and tool-result replay. Authenticated tests require the corresponding provider key; fixture-server checks do not establish account access or live model quality.
