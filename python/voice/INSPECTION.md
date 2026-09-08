# DeepSeek Harness inspection and voice design

Inspected baseline: `5dda764ed3aa172535a7967b06ff95d9cbfe536a`, version `0.1.5-alpha.1`, on Windows x64. This is a source and architecture inspection of the integration surfaces below, not a security audit or a claim that every file in the 288-project monorepo has been reviewed.

## Findings and preservation requirements

| Surface inspected | Finding | Voice integration decision |
| --- | --- | --- |
| `docs/architecture.md`, `docs/cordis-primer.md`, `packages/bundle/base/cordis.patch.yml` | Cordis plugins compose services, providers, consumers, and reversible lifecycle effects. `web`, `sdk`, `headless`, and `acp` build on the full base. | Use the full `sdk` profile. Do not substitute an ordinary chat completion loop or use `sdk-minimal`. |
| `packages/core/agent-loop`, `packages/core/session` | The runtime owns tool iterations and an append-only event history. Model-visible input must be logged. | Submit the reviewed transcript as an ordinary user message through the official SDK. Preserve the original ASR result in the local voice session export. |
| `packages/sdk/protocol/src/types.ts`, `packages/sdk/server/src/server.ts` | JSON-RPC exposes initialization, prompt enqueue, shutdown, and session/subagent notifications. It has no public per-turn cancel or interactive approval-response method. | Keep SDK ownership in one worker. Show tool and subagent activity. Do not invent RPC methods or auto-approve requests. Interactive workspace administration remains available in the upstream UI. |
| `python/sdk/src/deepseek_harness/api.py`, `client.py` | SDK owns initialization deadlines, child lifecycle, notification ancestry, final-response selection, session IDs, and shutdown. | Reuse the repository SDK and matching built runtime. Maintain a session ID across turns. Never retry an ambiguous agent turn automatically. |
| `packages/interaction/permission-presets`, `packages/bundle/sdk-app` | Permissions combine sandbox and approval configuration; profiles determine enforcement. | Leave upstream policy in force. Transcript review authorizes sending text, not a universal tool approval. Voice is an untrusted input channel. |
| `packages/llm/llm`, `llm-deepseek`, `llm-pi-ai` | Provider registration and model routing are runtime capabilities. | Let the full Harness resolve models and plugins. Local ASR selection does not remove LLM routing. |
| `packages/session/session-persistence-jsonl`, `session-projection`, `session-telemetry` | Durable events underpin history, projection, and telemetry. | Preserve runtime persistence. Collect ASR duration, inference latency, real-time factor, and review reasons separately; do not call decoder scores calibrated confidence. |
| `packages/subagent`, `packages/workflow`, `packages/skill`, `packages/client` | Agent capabilities live in independent plugin groups. | No removals or edits to these groups. The upstream desktop and web applications remain in the fork. |
| `apps/desktop/README.md`, `package.json`, `apps/desktop-host` | Existing Electron app owns a reserved profile, matching dependency seed, rollback, and a portless transport. Its built-in shell languages are English and Chinese. | Preserve it. Add a Python native voice workspace using the existing full SDK. This is a separate desktop entry, not a claim that the upstream Electron UI is fully translated into Japanese. |
| `python/sdk-runtime`, `scripts/build-exe-for-python-sdk.ts` | Windows runtime packaging includes the full CLI and native sidecars without requiring system Node. | Package that same-checkout runtime beside the Python desktop executable. Retain licenses and runtime sidecars. |
| `SAFETY.md`, upstream CI workflows | Developer preview, no security-audit claim; CI uses upstream-specific enterprise runners and secrets. | Describe portfolio readiness honestly. Add independent voice checks on standard runners. Production cloud and signed release qualification remain distinct work. |

## Speech quality design

Local faster-whisper with multilingual `large-v3` is the accuracy-oriented default candidate. `turbo` is an explicitly selected latency candidate. Neither is asserted to be the best model for this employer without measurements. CPU uses int8; optional CUDA uses float16 and requires compatible CUDA libraries. Model downloads are cached outside the repository. A cold model download is distinct from warm inference latency.

Japanese and English can be selected explicitly. Automatic detection is useful for exploration but less reliable on short utterances; mixed-language recordings must be evaluated separately. ASR uses `task=transcribe`, never translation. Kana, kanji, English terms, numbers, and proper names are retained without an LLM rewriting pass. User glossary terms bias decoding but can also introduce errors and need an ablation comparison.

Voice activity detection, a quiet-audio precheck, bounded audio duration, deterministic initial decoding, and disabled previous-text conditioning reduce specific failure modes. They cannot eliminate hallucinations. Low decoder scores, possible non-speech, uncertain language detection, and clipping remain explicit review reasons. Every transcript is editable before sending it to the agent.

Speaker diarization is separate from speech recognition. ASR segments are not speaker labels. No fabricated speaker attribution is displayed. Multi-speaker evaluation needs human speaker-turn labels, overlap annotations, and diarization error rate before a diarization provider can be qualified. The existing provider architecture can host a company model; no access to that proprietary model is assumed.

## Evaluation protocol

User-selected sources:

| Recording | Observed metadata | Intended coverage |
| --- | --- | --- |
| https://www.youtube.com/watch?v=lBVtvOpU80Q | GitLab Unfiltered, Product Marketing Meeting (weekly) 2021-06-28; English; 2,561 seconds | Meeting speech, multiple participants, business vocabulary, pauses |
| https://www.youtube.com/watch?v=J_1p8pCcFPU | Easy Japanese, EP017 (N2-N1), Natural Japanese Speaking Style; Japanese; 941 seconds | Natural Japanese delivery, particles, fillers, sentence boundaries |

Audio and captions remain in ignored local evaluation storage. Commit source IDs, timestamp windows, model configuration, hashes, aggregate scores, and reference provenance; do not redistribute recordings. Auto-captions are a weak reference and measure caption agreement, not verified ASR accuracy. Human-checked references are needed before quality gates can support a production claim.

Use disjoint development and held-out windows. Report Japanese CER, English WER, mixed-language CER, exact preservation of critical entities, and silence hallucination count. Preserve numbers in normalization. Aggregate edit distances by reference units, not by averaging clip percentages. Empty references have no error-rate denominator and are scored as silence cases. Report model load time, warm p50/p95 latency, real-time factor, hardware, sample count, and failures. Two recordings cannot establish performance across dialects, microphones, accents, or noisy environments.

## Operational design and remaining qualification

Local microphone audio stays in memory and is released after transcription. Importing a recording does not upload it. Only reviewed text is submitted to the configured Harness model provider, where normal API charges apply. Harness persists submitted conversations under its explicit application home; exports are user initiated. No API keys belong in source, exports, or screenshots.

Avoid automatic LLM retries in the voice layer: a timed-out tool-using request may already have changed files. Surface the failure and keep the draft. Model loading and inference run outside the UI thread. Inference is serialized to bound memory. Full-duplex interruption, streaming partials, cloud ASR failover, diarization, calibrated uncertainty, and automated model selection require additional measured milestones.

For an AWS service, deploy the speech provider separately from the desktop: authenticated requests, per-tenant authorization, explicit regional retention, bounded concurrency, GPU capacity alarms, request IDs, and latency/error dashboards. Do not move the unrestricted local agent runtime into a public container. No AWS deployment or uptime/SLO achievement is claimed by this local build.

## Primary references

- https://github.com/deepseek-ai/deepseek-harness
- https://github.com/SYSTRAN/faster-whisper
- https://huggingface.co/Systran/faster-whisper-large-v3
- https://github.com/pyannote/pyannote-audio
