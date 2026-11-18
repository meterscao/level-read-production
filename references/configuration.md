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

Local `align-audio` uses no private configuration. Its managed Python runtime defaults to `~/.codex/level-read-production/alignment-runtime/.venv/bin/python` and verified models to the sibling `models/` directory. `LEVEL_READ_ALIGNMENT_PYTHON` / `LEVEL_READ_ALIGNMENT_MODEL_DIR`, or the corresponding CLI flags, override these paths for isolated testing. Set `LEVEL_READ_PUNKT_DIR` to use a different local directory for the verified English sentence data. Alignment stops if required local dependencies are missing or fail verification. See [audio alignment](audio-alignment.md).

## PostgreSQL ingestion

Use an already authorized SSH alias to the production Docker host (`pg_primary.ssh_host`, default `qcloud-CD`) and the exact Website Swarm service (`pg_primary.service`, default `levelread-levelreadwebsite-2jbjx9`). Host-key verification is mandatory. No local Node or PG package installation is required. Never copy DATABASE_URL, database passwords, or production signing keys into this skill configuration.

The bridge selects the single desired running service task and runs the restricted PG runtime inside that container. News and twelve translations commit atomically. Credentials stay in the container.

Retry incomplete PG receipts with unchanged inputs in the same archive directory. Deterministic IDs and an exact content digest reuse an already committed result; completed receipts reject another insertion. Never discard an unrecognized receipt to force a write.

The runtime uses verified TLS and sets the business-write flag inside write transactions. The database schema enforces the write guard on editorial tables. `doctor` is offline; use `inspect` with the package, editorial review and both translation files to verify live PG access. See [pg-ingest-troubleshooting.md](pg-ingest-troubleshooting.md).
