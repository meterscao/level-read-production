---
name: level-read-production
description: "Create, revise and ingest Level Read learning news: supplied-copy adaptations, three CEFR levels, vocabulary, quizzes, 5:3 covers, audio, six-language translations and unpublished PostgreSQL records. Use for Level Read editorial or CMS requests, including title-only, cover-only and local-validation follow-ups. Respect the requested scope; generic writing, image editing or database work outside Level Read does not require this skill."
---

# Level Read Production

Work in Codex with the bundled standard-library Python publisher; the colleague does not install software or provide a website checkout. PostgreSQL is the only CMS backend. Keep credentials private and use the current installed script in resumed chats.

## Choose the requested operation

| Request | Work to perform |
| --- | --- |
| Full news production | Three readings, vocabulary/quizzes, cover, audio, exact word timelines and verified COS assets. Stay unpublished; do not ingest unless requested. |
| Local draft or validation | Create/check only the requested files. No image, TTS, upload or database connection unless asked. |
| Local MP3 alignment | Use `align-audio` for archived MP3s and their exact text; no TTS, COS or PG. Read [audio alignment](references/audio-alignment.md). |
| Title or cover revision | Reuse the current story and unchanged assets. Follow [revision guidance](references/revisions.md); do not rerun the full pipeline. |
| Translation preparation | Translate only requested fields/languages; six complete languages are required for ingest. Local preparation does not authorize ingest. |
| Ingest | Reuse the final approved package and assets. Prepare missing translations, validate locally, inspect PG, then insert only if needed. |
| Configuration/status check | `doctor` checks local configuration; `inspect` checks a story in live PG. Neither inserts records. |

A named artifact limits the task: “only the cover” does not request articles or audio. Honor explicit titles and visual directions before applying default editorial preferences.

## Source and headline decisions

Read [source handling](references/source-research.md). If asked to rewrite supplied copy without a second fact check, use only that copy and record that it was not independently verified. Do not label it verified or invent source links. Research short leads or ordinary news requests when verification is needed. Missing facts are not permission to invent them.

Keep a title explicitly chosen by the user verbatim. Otherwise use the headline process in [package contract](references/package-contract.md): identify the concrete hook, compare three distinct angles, and choose a clear, faithful learner-facing title. A question is appropriate when the reading answers that question; do not turn a qualified trend into a universal claim.

## Produce a new story

1. Record the source basis, dates, attribution and limits. Save the three-level object as `news-complete.json` using [package contract](references/package-contract.md): Level 1 A1–A2, 100–120 words/3 vocabulary/1 quiz; Level 2 B1–B2, 150–180/4/2; Level 3 C1–C2, 180–220/5/3. Preserve paragraphs and material caveats at every level. Use Codex for text generation.
2. Generate `blind-quiz.json` with `review-sheet`. Answer each question from its own reading, recording exact option text, evidence and reasons for rejecting the alternatives in `editorial-review.json`. Do not derive decisions from answer indices or claim a blind review that was not performed. Source verification and quiz correctness are separate checks.
3. Run `validate` locally before any billable step. It checks a copy in memory, including the quiz normalization used by `produce`; it does not modify input files. Provide the review when ready. Validation without a review is not editorial approval.
4. Read [cover direction](references/cover-direction.md). Plan the subject/reference, visible relationship, palette and negative space; use the image tool. Inspect the image and export the approved 1500 × 900 sRGB PNG. A supplied reference anchors the subject; a simplified or symbolic cover follows the user's direction and must not be described as documentary evidence.
5. Run `produce` with the review, cover, source and date. It archives to `~/Documents/Level Read Production/YYYY-MM-DD-titleid/`, creates audio, aligns all three levels, validates their exact source/hash bindings, and uploads immutable MP3/timeline assets with full readback before writing a complete package. Run `review-check` on the final package after option shuffling. Use `--resume` only for unchanged inputs after a transient failure; never to apply revised wording or a new cover.

Read [internal commands](references/commands.md) for exact invocations. Read [configuration](references/configuration.md) only for setup, missing fields or connection details. Keep intermediate work separate from user-facing deliverables.

Default `produce` now checks the local alignment runtime before TTS, generates all three timelines, and writes `audio` plus `audioTiming` for each level after immutable COS upload and signed/public byte verification. Alignment or verification failure stops production; do not mark a package complete without its timelines. Read [audio alignment](references/audio-alignment.md). For an explicitly requested local listening checkpoint, `produce --align-audio` still pauses before every upload and returns `audio_alignment_review_required`; standalone `align-audio` remains local-only. Structural checks and successful publication never imply that a person manually reviewed acoustic accuracy.

## Prepare and ingest

Read [translations](references/body-translations.md). Translate the final English title itself into `zh-CN`, `zh-TW`, `ja`, `ru`, `es`, `pt-BR`; back-translate to catch changes in subject, action, scope, purpose or uncertainty. Do not add article-only names/details. Translate summaries, level titles and article paragraphs faithfully; quizzes and vocabulary explanations remain English. Bind `body-translations.json` to the final source fingerprint.

English remains the source. For new packages, run `validate` with the review and both six-language artifacts, then `inspect`:

- `missing`: the user's ingest request authorizes the normal unpublished insertion.
- `existing` and all news/title/body checks match, with six READY titles for the inspected languages: report the PG ID. Additional cached languages appear separately in the result.
- Different, incomplete, ambiguous or published content: report the discrepancy without overwriting it.

For a new ingest, preserve the complete story directory: original MP3s, `audio-timings/` outputs, final package and upload receipt. `ingest` verifies all three timing references against local bytes/text, then freshly reads the configured COS objects with production and local origins before PG. Missing or stale timing stops before insertion. `inspect` continues to support historical packages without timing; do not rewrite completed legacy receipts or re-ingest old news to add derived data.

`ingest` requires `public: false` and commits one news row plus twelve translations in one transaction. Unchanged retries reuse deterministic IDs/content digests. Preserve receipts; retry an incomplete PG attempt in its original directory. For an archived Korean-set package, follow the [historical translation rules](references/body-translations.md#historical-packages). Once an ingest receipt exists, including an unsuccessful or uncertain attempt, do not run `produce` again; preserve the exact package and retry `inspect`/`ingest`. Never bypass a completed receipt or conflict by staging another copy. After insertion, inspect again and record the backend, PG ID and receipt in `production-state.json`. See [PG troubleshooting](references/pg-ingest-troubleshooting.md) for failures.

## Report the result

Always state the exact final English headline and prepared Simplified Chinese title. Link the deliverables and state source basis, QA and production/ingest status accurately. Distinguish local validation, generated media, uploaded assets and committed PG records. On failure, use `production-state.json`/the PG receipt to identify the actual stage; do not claim a later stage succeeded.
