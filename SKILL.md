---
name: level-read-production
description: Produce complete Level Read news items directly in Codex. Use whenever the user gives verified news content and asks for a 5:3 text-free cover, Level 1/2/3 learning articles, vocabulary and quizzes, audio, a Level Read package, or to submit an unpublished Level Read story to CMS. This skill generates the content and cover in Codex, then uses its bundled zero-dependency publisher script for Tencent COS uploads and optional CloudBase ingest.
---

# Level Read Production

Run this skill entirely inside Codex. The colleague never installs Node, npm, Python, a binary, or the website repository. Codex supplies the internal Python runtime that executes the bundled publisher script.

## First use

Read `references/configuration.md` if configuration is absent. The one-time configuration file is local to the installed skill and is never uploaded or printed. Do not ask the user to run a terminal command; guide them to provide or place the configuration only when setup is needed.

## Production workflow

1. Read `references/source-research.md`. Build a verified fact brief from the supplied article, or research the event when the user supplies only a title or short summary. The user may supply `manual-input:<reason>` in place of a source URL only when that is deliberate.
2. Read `references/package-contract.md`, then generate the three levels from the verified fact brief in that `NewsComplete` JSON contract. Before drafting the headline, apply its headline-fidelity check against the fact brief; follow the title, short-summary, paragraph, vocabulary, and quiz-evidence requirements exactly. Do not call an external text model for this step: use Codex's own generation ability.
3. Read `references/cover-direction.md`, then generate the cover with the image-generation tool. Keep it locally until the publisher runs.
4. Save the three-level object as `news-complete.json`, then call the bundled Python script's `produce` command. It creates a stable local archive at `~/Documents/Level Read Production/YYYY-MM-DD-titleid/`, copies the cover there, validates and normalizes the package, generates all audio locally, then uploads the cover and audio to COS.
5. Report the source links used, artifact directory, `production-state.json`, and QA state. If `produce` fails, use the recorded stage to state precisely whether audio generation, cover upload, or an audio upload failed. Do not ingest by default.
6. Only when the user explicitly says add, ingest, import, or write to CMS, call `ingest` with `--confirm-unpublished-ingest`.

For a corrected transient failure, rerun the same story with `--resume`. It reuses local audio and any uploaded asset URLs recorded in `production-state.json`; use it only when the content and cover are unchanged.

## Internal commands

The commands below are for Codex to execute, not instructions for the colleague. Resolve the script path relative to this skill directory.

```bash
python3 scripts/publisher.py doctor

python3 scripts/publisher.py produce \
  --levels /absolute/path/news-complete.json \
  --cover /absolute/path/cover.png \
  --original-url https://example.com/source \
  --date 2026-08-23

python3 scripts/publisher.py ingest \
  --input "/Users/name/Documents/Level Read Production/2026-08-23-story-title/news-package.json" \
  --confirm-unpublished-ingest
```

## Publication safety

- `produce` always writes `public: false` and never creates a CloudBase record.
- `ingest` rejects any package with `public` other than `false`.
- Never print configuration values, HTTP authorization headers, or secret values.
- If an asset upload succeeds but a later step fails, report the local artifacts and the failure. Do not claim the story was ingested.
