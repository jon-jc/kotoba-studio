---
description: "Kotoba Studio sidebar and conversation branding for this fork."
kind: "package-reference"
---

# @deepseek-ai/dsh-client-ui-brand-official

English | [中文](README.zh.md)

## Summary

This fork uses Kotoba Studio artwork and a language-invariant product name in the sidebar and blank-conversation hero. The upstream package identity remains stable for plugin compatibility. All client build profiles receive these occupants and a Japanese language pack. Provider names, model IDs, licenses, and source attribution retain their original identities.

## Table of Contents

- [Use this package](#use-this-package)
- [Understand the implementation](#understand-the-implementation)
- [Further Exploration](#further-exploration)
- [Model Experience](#model-experience)
- [Known Limitations and Deferred Work](#known-limitations-and-deferred-work)
- [Dev Note](#dev-note)

## Use this package

Mount the existing package in the browser roster. Its three occupants fill `sidebar.brand.mark`, `sidebar.brand.name`, and `conversation.hero.brand.mark`. To supply another brand, replace this package with a plugin occupying those slots. The browser title is configured separately by `DSH_CLIENT_TITLE`; this fork's official title and localized fallback are Kotoba Studio.

Japanese covers chat, composer, workspaces, model selection, model settings, and shared controls. Other extension keys fall back to English. The native English/Japanese selector changes the browser locale without reloading; messages, drafts, code, and model responses retain their original text.

## Understand the implementation

The theme service owns the user's light/dark preference. This plugin registers paired neutral charcoal and muted jade tokens, a Japanese language pack, and a desktop language listener; each registration is disposed with the plugin.

The sidebar mark and name register together after both sidebar declarations exist. The hero registers independently when its conversation declaration exists. Each set withdraws with its declaration or plugin fiber. This supports either activation order without coupling sidebar availability to conversation loading. The [browser entry](src/client/index.ts) registers the [artwork](src/client/Brand.tsx); the node entry has no effects.

## Further Exploration

- [Sidebar](../ui-sidebar/README.md) declares the sidebar slots.
- [Conversation](../ui-conversation/README.md) declares the hero slot.
- [Desktop branding](../../../python/voice/README.md) describes native and installer artwork.

## Dev Note

No invariant companion is published: the package retains no mutable state, and all occupants leave through their owning slot effects.

## Model Experience

None, as this package contributes browser presentation only; nothing here reaches a model request.

#### KV Cache effect

None; the package neither assembles nor sends provider requests.

## Known Limitations and Deferred Work

- Only one occupant set is supplied. Browser titles and native executable icons have separate owners. The upstream fallback artwork remains available to profiles that explicitly omit this plugin.
