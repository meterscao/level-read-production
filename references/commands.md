# Internal commands

Resolve the publisher path relative to the installed skill. These commands are for Codex.

## Production and editorial checks

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
    { "languageCode": "ru", "title": "Заголовок на русском" },
    { "languageCode": "es", "title": "Titular en español" },
    { "languageCode": "pt-BR", "title": "Título em português do Brasil" }
  ]
}
```


## Local validation, no configuration or network access

```bash
python3 scripts/publisher.py validate --input /absolute/path/news-complete.json

python3 scripts/publisher.py validate \
  --input /absolute/path/news-package.json \
  --editorial-review /absolute/path/editorial-review.json \
  --title-translations /absolute/path/title-translations.json \
  --body-translations /absolute/path/body-translations.json
```

Optional review/translation arguments check only the supplied artifacts. Body translation validation requires title translations. Both artifacts use the current six targets for new packages. Use [historical package rules](body-translations.md#historical-packages) for an archived Korean-set package. A missing review is reported as not provided, never as approved. Input files remain unchanged; balanced quiz positions are checked after in-memory normalization, matching `produce`.

## Default timing behavior

The normal `produce` command above needs no timing flag: it requires the pinned local alignment runtime, aligns all three generated MP3s and writes immutable verified COS URLs plus `audioTiming` per Level. Preserve `audio-timings/`, MP3s and `audio-timing-upload.json` with the final package. `ingest` rejects missing or stale timing and freshly verifies COS before PG; it stays unpublished and never changes an existing completed story. Do not rerun TTS to repair historical news; align its existing exact audio/text in the separate repair flow.

`--align-audio` retains the explicit local review pause: it stops before every upload. For normal end-to-end production omit that flag. Local-only `validate`, `review-sheet`, `review-check` and standalone `align-audio` do not acquire upload/ingest authorization from this default.

## Local MP3 alignment

```bash
python3 scripts/publisher.py align-audio \
  --input /absolute/path/news-package.json \
  --output /absolute/path/separate-alignment-output \
  --resume
```

Defaults to all three levels and MP3s beside the input package. `--level 2` limits the run, and `--audio-dir` selects a different local MP3 directory. This command does not read credentials or use TTS, COS or PG. It copies inputs into a separate output directory, writes schema-v1 timelines, raw results, quality reports and a listening page. See [runtime and review details](audio-alignment.md).

For a newly generated story, add `--align-audio` to `produce`: it aligns after local TTS and returns at a local review checkpoint before any upload. It does not generate a finished `news-package.json` in this mode, does not upload timeline JSON and does not attach `audioTiming` to online data.

## Read-only PG inspection

```bash
python3 scripts/publisher.py inspect \
  --input /absolute/path/news-package.json \
  --editorial-review /absolute/path/editorial-review.json \
  --title-translations /absolute/path/title-translations.json \
  --body-translations /absolute/path/body-translations.json
```
