# Configuration

The internal standard-library Python script reads `~/.codex/level-read-production/config.json`. This private file is separate from the installed skill, survives upgrades, and must never be shared. `LEVEL_READ_PRODUCTION_CONFIG` overrides its location for controlled testing.

```json
{
  "ai": {
    "base_url": "https://aihubmix.com/v1",
    "api_key": "replace-me",
    "tts_model": "tts-1",
    "tts_voice": "shimmer"
  },
  "cos": {
    "secret_id": "replace-me",
    "secret_key": "replace-me",
    "bucket": "replace-me-appid",
    "region": "ap-guangzhou"
  },
  "pg_primary": {
    "ssh_host": "qcloud-CD",
    "service": "levelread-levelreadwebsite-2jbjx9"
  }
}
```

AI and COS settings are used for audio and asset uploads. `doctor` only checks required fields; it makes no network requests or writes.

## PostgreSQL ingestion

Use an already authorized SSH alias to the production Docker host (`pg_primary.ssh_host`, default `qcloud-CD`) and the exact Website Swarm service (`pg_primary.service`, default `levelread-levelreadwebsite-2jbjx9`). Host-key verification is mandatory. No local Node or PG package installation is required. Never copy DATABASE_URL, database passwords, or production signing keys into this skill configuration.

The bridge selects the single desired running service task, then executes the pinned bundled PG runtime through `docker exec` inside that container. Credentials remain there. News and twelve translations commit atomically. No CloudBase credentials, dual-write switches, task queue or worker image are used.

Retry an incomplete PG receipt with the exact same ingest inputs; deterministic IDs and an exact content digest reuse an already committed result. A completed receipt rejects another ingest. Legacy CloudBase receipts require separate review and are never replayed automatically.
