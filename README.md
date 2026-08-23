# Level Read Production

Standalone Codex skill for producing a Level Read news item: three reading levels, a text-free cover, audio, Tencent COS upload, and optional unpublished CloudBase ingestion.

This repository *is* the skill. It has no website, Node, npm, package-manager, binary, or third-party Python dependency. Codex generates the editorial content and cover; the bundled Python standard-library script validates the package, requests AI HubMix TTS, uploads assets, and optionally creates an unpublished CMS record.

## Installation

Install this repository as the `level-read-production` skill from GitHub in Codex. Do not clone the website repository.

Create `~/.codex/level-read-production/config.json` from [`config.example.json`](config.example.json) and supply the team's AI HubMix, Tencent COS, and CloudBase credentials. Keep that local configuration out of Git.
