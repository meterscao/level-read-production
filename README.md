# Level Read Production

Standalone Codex skill for producing a Level Read news item: three reading levels, a text-free cover, audio, Tencent COS upload, six localized titles, and optional unpublished CloudBase ingestion.

This repository *is* the skill. It has no website, Node, npm, package-manager, binary, or third-party Python dependency. Codex generates the editorial content and cover; the bundled Python standard-library script validates the package, requests AI HubMix TTS, uploads assets, and optionally creates an unpublished CMS record.

## Installation

Install this repository as the `level-read-production` skill from GitHub in Codex. Do not clone the website repository.

Create `~/.codex/level-read-production/config.json` from [`config.example.json`](config.example.json) and supply the team's AI HubMix, Tencent COS, and CloudBase credentials. Keep that local configuration out of Git.

## Local output

Every run is archived locally at `~/Documents/Level Read Production/YYYY-MM-DD-titleid/`. The directory contains the original cover, three audio files, the generated level package, upload metadata, QA result, and `production-state.json`. Files remain there after upload so a story can be checked or ingested later. If production stops, `production-state.json` records the exact failed stage.

Before an explicit CMS ingest, Codex creates a reviewed `title-translations.json` alongside the package. It contains localized versions of the final title for Simplified Chinese, Traditional Chinese, Japanese, Korean, Spanish, and Brazilian Portuguese. The publisher validates that artifact, then creates the unpublished news record and its six `enli_news_title_translation` records.

After a transient production failure, rerun the unchanged story with the publisher's internal `--resume` option. It reuses local audio and skips already recorded uploads.
