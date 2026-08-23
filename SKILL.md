---
name: level-read-production
description: Produce complete Level Read news items directly in Codex. Use whenever the user gives verified news content and asks for a 5:3 text-free cover, Level 1/2/3 learning articles, vocabulary and quizzes, audio, a Level Read package, or to submit an unpublished Level Read story to CMS. This skill generates the content and cover in Codex, then uses its bundled zero-dependency publisher script for Tencent COS uploads and optional CloudBase ingest.
---

# Level Read Production

Run this skill entirely inside Codex. The colleague never installs Node, npm, Python, a binary, or the website repository. Codex supplies the internal Python runtime that executes the bundled publisher script.

## First use

Read `references/configuration.md` if configuration is absent. The one-time configuration file is local to the installed skill and is never uploaded or printed. Do not ask the user to run a terminal command; guide them to provide or place the configuration only when setup is needed.

## Production workflow

1. Obtain verified source text, source URL, and publication date. The user may supply `manual-input:<reason>` in place of a source URL only when that is deliberate.
2. Generate the three levels yourself in the `NewsComplete` JSON contract from `references/package-contract.md`. Do not call an external text model for this step: use Codex's own generation ability.
3. Generate the cover with the image-generation tool using `references/cover-direction.md`; save it as a local PNG in the story work directory.
4. Save the three-level object as `news-complete.json`, then call the bundled Python script's `produce` command. It validates and normalizes the package, generates audio through the configured AI gateway, uploads the cover and audio to COS, and creates `news-package.json`.
5. Report the artifact directory and QA state. Do not ingest by default.
6. Only when the user explicitly says add, ingest, import, or write to CMS, call `ingest` with `--confirm-unpublished-ingest`.

## Internal commands

The commands below are for Codex to execute, not instructions for the colleague. Resolve the script path relative to this skill directory.

```bash
python3 scripts/publisher.py doctor

python3 scripts/publisher.py produce \
  --levels /absolute/path/news-complete.json \
  --cover /absolute/path/cover.png \
  --original-url https://example.com/source \
  --date 2026-08-23 \
  --output /absolute/path/story-output

python3 scripts/publisher.py ingest \
  --input /absolute/path/story-output/news-package.json \
  --confirm-unpublished-ingest
```

## Publication safety

- `produce` always writes `public: false` and never creates a CloudBase record.
- `ingest` rejects any package with `public` other than `false`.
- Never print configuration values, HTTP authorization headers, or secret values.
- If an asset upload succeeds but a later step fails, report the local artifacts and the failure. Do not claim the story was ingested.
