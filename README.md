# Level Read Production

Standalone Codex skill for producing a Level Read news item: three reading levels, a text-free cover, audio, Tencent COS upload, six localized titles, and optional unpublished PostgreSQL ingestion.

This repository *is* the skill. It has no website, Node, npm, package-manager, binary, or third-party Python dependency. Codex generates the editorial content and cover; the bundled Python standard-library script validates the package, requests AI HubMix TTS, uploads assets, and optionally creates an unpublished CMS record.

## Installation

Install this repository as the `level-read-production` skill from GitHub in Codex. Do not clone the website repository.

Create `~/.codex/level-read-production/config.json` from [`config.example.json`](config.example.json) and supply the team's AI HubMix, Tencent COS, and an approved SSH host/service for PG ingestion. Keep that local configuration out of Git.

## Local output

Every run is archived locally at `~/Documents/Level Read Production/YYYY-MM-DD-titleid/`. The directory contains the original cover, three audio files, the generated level package, upload metadata, QA result, and `production-state.json`. Files remain there after upload so a story can be checked or ingested later. If production stops, `production-state.json` records the exact failed stage.

Before an explicit CMS ingest, Codex creates a reviewed `title-translations.json` alongside the package. It contains localized versions of the final title for Simplified Chinese, Traditional Chinese, Japanese, Korean, Spanish, and Brazilian Portuguese. The publisher validates that artifact, then creates the unpublished news record and its six `enli_news_title_translation` records.

After a transient production failure, rerun the unchanged story with the publisher's internal `--resume` option. It reuses local audio and skips already recorded uploads.

PG-only ingest uses the existing Website container via SSH; no local database credentials, CloudBase access, source synchronization or retry worker. See SKILL.md.

## 六张迁移表退役（2026-10-22）

当前 PG 代码不依赖主库归属、字段归属、同步状态或删除 ID 登记表；固定源为 Website e4bd6cfac4530e29b4571e236b7a10bc2779558d。仅保留业务事务、并发锁、归属检查和支付/推送等业务幂等保护，不新增替代表。历史迁移说明仅供追溯，不是当前运行方式。旧 API 和 Expo 不在本次范围。

## PG 业务模型（2026-10-24）

运行时与测试 schema 同时固定到上述 Website 提交。每日活动、会员权益已关系化；新闻内容/翻译仍保留适合的有界 JSON。导入维持未发布、物理 ID、逻辑键、事务与重试幂等保护。按 Website 的 expand → backfill → 四入口发布 → contract 顺序上线。

### JSON 存储精简

共享运行时固定到 Website `e4bd6cfac4530e29b4571e236b7a10bc2779558d`。完整业务对象由类型列、保留的内容 JSON 和稀疏扩展字段重建，保留字段缺失、显式 null 和历史值差异。必须先应用 `pg-json-storage/001-expand.sql`，四个入口更新后才能分批清理重复副本并收尾。推送控制字段使用现有表中的类型列；每日活动、会员权益及身份、事务、业务幂等保护继续保留。
