---
name: level-read-production
description: Produce complete Level Read news items directly in Codex. Use whenever the user gives verified news content and asks for a 5:3 text-free cover, Level 1/2/3 learning articles, vocabulary and quizzes, audio, a Level Read package, or to submit an unpublished Level Read story to CMS. This skill generates the content and cover in Codex, then uses its bundled zero-dependency publisher script for Tencent COS uploads and optional PostgreSQL ingest.
---

# Level Read Production

Run this skill entirely inside Codex. The colleague never installs Node, npm, Python, a binary, or the website repository. Codex supplies the internal Python runtime that executes the bundled publisher script.

## First use

Read `references/configuration.md` if configuration is absent. The one-time configuration file is local to the installed skill and is never uploaded or printed. Do not ask the user to run a terminal command; guide them to provide or place the configuration only when setup is needed.

## Production workflow

1. Read `references/source-research.md`. Build a verified fact brief from the supplied article, or research the event when the user supplies only a title or short summary. The user may supply `manual-input:<reason>` in place of a source URL only when that is deliberate.
2. Read `references/package-contract.md`, then write the news spine and identify the verified fact most likely to make a learner want to open the story: a surprising action, visible change, contrast, scale, consequence, or human stake. Draft three genuinely different headline angles around that fact, rather than three safe paraphrases. For each, test what a learner understands from the headline alone and what specific question it makes them want answered. Choose the most inviting headline that still states the core fact faithfully in learner-friendly English. Keep a mechanism or approximate number when it is what makes the event distinctive and understandable; move only secondary details to the summary. Reject clickbait, unexplained jargon, and unfamiliar names that do not help a cold reader understand the event. Prefer a direct event headline; use a question only when it expresses the article's real central question. Write Level 1 for A1–A2, Level 2 for B1–B2, and Level 3 for C1–C2; calibrate article, vocabulary explanations, and quizzes together. Do not call an external text model for this step: use Codex's own generation ability.
3. Read `references/cover-direction.md`, then make a cover plan before prompting the image model: state the subject-reference decision; individual-or-group subject choice; story verb; single, deliberately secondary vector structure; limited palette; named pale canvas tone; supporting context; and topic-specific exclusions. Generate the text-free cover with the image-generation tool. Inspect it against the cover acceptance gate and regenerate it if required visual elements or constraints are absent. Export the approved canonical 1500 × 900 master as an sRGB PNG. Keep it locally until the publisher runs.
4. Save the three-level object as `news-complete.json`. Run `review-sheet` to make `blind-quiz.json`, then follow the blind review in `references/package-contract.md`: answer all six questions from their own level's reading without seeing the draft answer key, record exact selected option text, a short source quotation, and reasoning in `editorial-review.json`, and repair any wrong or ambiguous question before continuing. The correct option may paraphrase the reading; its meaning must be obvious from the current level and factually correct. Check that Level 1's one quiz asks one short question about one idea, even when the reading contains several important facts. Re-run both headline tests against the final title: can a learner explain its core fact without article context, and does the verified hook give them a concrete reason to open it? Record the hook and the reader's likely question in the headline review. Account for every potentially unfamiliar proper noun, technical phrase, or abstract term in `termChecks`; omit or rewrite details that do not help the cold read. Do not approve a title because its rationale explains it. Never fill the quiz review from the existing answer indices.
5. Run `produce` with `--editorial-review`. It checks the review before any audio generation or upload, creates a stable local archive at `~/Documents/Level Read Production/YYYY-MM-DD-titleid/`, copies the cover there, normalizes the quiz option positions, generates all audio locally, then uploads the cover and audio to COS. Run `review-check` against the archived final `news-package.json` and `editorial-review.json` to verify the reordered options still match the independently chosen answers.
6. Whenever the news content or package is ready, explicitly tell the user its final English headline in your reply. Do this whether the task ends with a draft, a produced package, or CMS ingest; never rely on the user opening an artifact to discover the title. If a Chinese title translation has been prepared, include the Simplified Chinese title alongside it. Also report the source links used, artifact directory, `production-state.json`, and QA state. If `produce` fails after the headline is finalized, still report the title and use the recorded stage to state precisely whether audio generation, cover upload, or an audio upload failed. Do not ingest by default.
7. Before any requested CMS ingest, use Codex to create `title-translations.json` in the same archive directory. Translate the final English `title` into all six required language codes: `zh-CN`, `zh-TW`, `ja`, `ko`, `es`, and `pt-BR`. Compare each translation directly with the final English title, checking that its subject, action, purpose, scope, and uncertainty have the same meaning. Use natural target-language wording, but never replace a generic English description with a specific name or add a detail found only in the article or fact brief. Back-translate each title into English and repair any added, missing, or changed meaning; pay special attention to both Chinese titles. Read `references/body-translations.md`, then create and review `body-translations.json` for the same six languages from the final package. It includes the reviewed titles, summary, and every level's article text. Call `ingest` with `--editorial-review`, `--title-translations`, `--body-translations`, and `--confirm-unpublished-ingest`. In the completion reply, repeat the exact final English headline and, when available, its `zh-CN` translation, and report the body translation result.

For a corrected transient failure, rerun the same story with `--resume`. It reuses local audio and any uploaded asset URLs recorded in `production-state.json`; use it only when the content and cover are unchanged.

## Internal commands

The commands below are for Codex to execute, not instructions for the colleague. Resolve the script path relative to this skill directory.

```bash
python3 scripts/publisher.py doctor

python3 scripts/publisher.py review-sheet \
  --input /absolute/path/news-complete.json \
  --output /absolute/path/blind-quiz.json

python3 scripts/publisher.py produce \
  --levels /absolute/path/news-complete.json \
  --editorial-review /absolute/path/editorial-review.json \
  --cover /absolute/path/cover.png \
  --original-url https://example.com/source \
  --date 2026-08-23

python3 scripts/publisher.py review-check \
  --input "/Users/name/Documents/Level Read Production/2026-08-23-story-title/news-package.json" \
  --editorial-review "/Users/name/Documents/Level Read Production/2026-08-23-story-title/editorial-review.json"

python3 scripts/publisher.py ingest \
  --input "/Users/name/Documents/Level Read Production/2026-08-23-story-title/news-package.json" \
  --editorial-review "/Users/name/Documents/Level Read Production/2026-08-23-story-title/editorial-review.json" \
  --title-translations "/Users/name/Documents/Level Read Production/2026-08-23-story-title/title-translations.json" \
  --body-translations "/Users/name/Documents/Level Read Production/2026-08-23-story-title/body-translations.json" \
  --confirm-unpublished-ingest
```

`title-translations.json` must use this exact shape and must match the final package title and `titleid` exactly:

```json
{
  "titleid": "story-title",
  "sourceTitle": "Final English headline",
  "translations": [
    { "languageCode": "zh-CN", "title": "简体中文标题" },
    { "languageCode": "zh-TW", "title": "繁體中文標題" },
    { "languageCode": "ja", "title": "日本語の見出し" },
    { "languageCode": "ko", "title": "한국어 제목" },
    { "languageCode": "es", "title": "Titular en español" },
    { "languageCode": "pt-BR", "title": "Título em português do Brasil" }
  ]
}
```

## Publication safety

- `produce` always writes `public: false` and never creates a database record.
- `ingest` rejects any package with `public` other than `false`.
- `produce` and `ingest` require a completed editorial review matching the exact current wording. Never modify an already published news record as part of this workflow.
- `ingest` rejects missing, incomplete, or mismatched title or body translations before any CMS write. It creates the unpublished news record, then writes six `READY` records to `enli_news_title_translation` and six article records to `enli_news_translation`, linked by its returned `newsId`.
- Never print configuration values, HTTP authorization headers, or secret values.
- If an asset upload succeeds but a later step fails, report the local artifacts and the failure. Do not claim the story was ingested.

## PostgreSQL ingest

CMS ingest directly writes PostgreSQL. It never accesses CloudBase or creates synchronization tasks. News, six READY title translations and six body translations commit in one PG transaction. An identical retry uses deterministic IDs and an exact content digest; changed content with the same titleid is rejected instead of overwriting an existing story.

The standard-library SSH bridge executes the pinned bundled runtime inside the running Website container. PG credentials stay inside that container; local configuration only selects the approved SSH host/service. No local Node installation is required.

`ingest-result.json` records intent before remote writes. On an incomplete PG receipt, rerun the same ingest command with unchanged input/review/translations; an ambiguous successful COMMIT is recognized and reused. A completed receipt prevents another ingest. Legacy CloudBase receipts require explicit review and are never replayed; `sync-ingest` is retired. Report failure without claiming ingestion succeeded. COS upload behavior is unchanged.
