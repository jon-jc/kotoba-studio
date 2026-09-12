# Agent Note: Bilingual team handoffs

Status: implemented

English | [中文](2026-09-12-bilingual-team-handoffs.zh.md)

## Problem

English- and Japanese-speaking teammates need to distinguish original meeting evidence, translated summaries, and confirmed commitments. A plain transcript does not record separate translation review or ownership.

## Decision

Kotoba stores bilingual handoffs separately from meeting transcripts. A handoff contains original context, terminology, editable English/Japanese briefs, and decisions, actions, or questions with ownership, dates, progress, quotes, and review marks. Meeting import creates an independent copy. Source or glossary edits invalidate all reviews; work-item edits invalidate that item's review except progress changes. SQLite schema version 1 and optimistic revisions protect local persistence and competing windows.

AI assistance prepares an unsent request in the existing voice draft; the user chooses a model, sends through the existing agent, and imports its JSON reply. The request asks for no tools but does not replace the agent's access policy. Cloud submission remains explicit. A source/glossary fingerprint rejects stale replies. Parsed fields are bounded and each imported work item requires an exact original quote. These checks cannot prove translation accuracy or entailment, so all imported material starts unreviewed. Replacement of existing translated work requires confirmation.

## Consequences

Copy and Markdown export include original text and review labels. There is no automatic task execution, messaging, remote synchronization, or shared account service. Local data remains after closing the dialog. Store conflicts leave newer persisted data intact and report unsaved edits.

## Alternatives considered

Silently translating meeting segments would mix source evidence with model output. Automatically assigning owners from inferred intent would make unconfirmed commitments appear agreed. A separate tool-enabled background agent would duplicate routing and authorization. The explicit request/import workflow retains the existing provider selection and review step, with additional interaction cost.

## Verification

Owner-local tests cover persistence, competing revisions, future-schema refusal, malformed responses, missing quotes, stale source/glossary fingerprints, exported uncertainty labels, and native editor review invalidation. English and Japanese native dialog previews use manually entered examples; they are not model-quality evidence. No external provider request is part of these checks.
