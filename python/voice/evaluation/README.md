# Voice evaluation results

These measurements compare local ASR with unverified YouTube captions from the two user-selected recordings in [sources.json](sources.json). They measure caption agreement, not human-verified recognition accuracy. Audio and transcripts are not redistributed.

Both models used CPU/int8, explicit English or Japanese, beam size five, transcription rather than translation, VAD, and no conditioning on previous text. Clips are 20 seconds long. Japanese uses character edit distance; English uses word edit distance. Punctuation is removed during scoring; numbers remain. Aggregate rates divide total errors by total reference units.

| Split | Language | Large-v3 | Turbo | Reference units |
| --- | --- | --- | --- | --- |
| Development: two clips | English WER | 3.06% | 5.10% | 98 words |
| Development: two clips | Japanese CER | 18.97% | 20.51% | 195 characters |
| Held out: one clip | English WER | 1.96% | 3.92% | 51 words |
| Held out: one clip | Japanese CER | 33.62% | 33.62% | 116 characters |

The held-out windows were excluded from the initial comparison. No parameters were tuned against their results. Large-v3 had lower English disagreement in these samples; the Japanese held-out disagreement remains substantial for both models. The sample is too small and its reference too uncertain to qualify either model for production, establish a general ranking, or support claims about accents, noise, code switching, names, or speaker attribution. Caption timing and arbitrary clip boundaries also need human review.

[Development records](development-results.json) and [held-out records](held-out-results.json) include sample hashes, settings, per-clip errors, and observed inference latency. Timing came from one Windows development laptop rather than a controlled latency benchmark. Model download/load latency is excluded from inference timing. Recognition runs locally, and every result remains editable before sending.

The next qualification dataset needs independently corrected transcripts, annotated clip boundaries, critical-name/number checks, silence/noise cases, mixed Japanese/English, and speaker labels before diarization can be evaluated. These supplied recordings remain useful examples within that broader test set.

## Language-specific defaults

[Language-default records](language-defaults.json) measure Parakeet Unified EN and Kotoba-Whisper v2 on the same three excerpts per language. English caption disagreement was 7/98 words on development excerpts and 8/51 on the held-out excerpt. Japanese disagreement was 25/195 characters and 45/116 respectively. Parakeet took 0.85–0.90 seconds per 20-second excerpt; Kotoba-Whisper took 13.24–13.58 seconds on this run. CPU timings vary with concurrent work. The held-out excerpt was already known from the earlier evaluation and is not a new blind qualification set. These defaults prioritize language-specific local usability, not a claim that they beat large-v3 on every recording. The recorded captions are unverified, and no audio or transcript is redistributed. Japanese word alignment is disabled for the distilled model; segment timestamps remain available.
