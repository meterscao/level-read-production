# Configuration

The skill's internal Python script reads `~/.codex/level-read-production/config.json`. Create it once from `config.example.json`; it is separate from the installed skill, survives skill upgrades, and must never be included in a shared skill archive. `LEVEL_READ_PRODUCTION_CONFIG` can override the location for controlled testing.

```json
{
  "ai": {
    "base_url": "https://aihubmix.com/v1",
    "api_key": "...",
    "tts_model": "tts-1",
    "tts_voice": "shimmer"
  },
  "cos": {
    "secret_id": "...",
    "secret_key": "...",
    "bucket": "bucket-appid",
    "region": "ap-guangzhou"
  },
  "cloudbase": {
    "env": "...",
    "secret_id": "...",
    "secret_key": "...",
    "region": "ap-guangzhou"
  }
}
```

`doctor` only checks whether required fields exist. It makes no network request, write, or billable model call.

## PG synchronization bridge

CMS ingest requires an authenticated existing SSH alias to the production Docker host. Defaults are `ssh_host=qcloud-CD`, `container_filter=levelread-levelreadwebsite-2jbjx9`, and the pinned existing worker image `sha256:7b1281e54210b9bd2e2474a49aa4a793389293f71dd43a2a726cc3002915001a`. Optional `pg_sync` configuration can override these values; SSH host-key verification is mandatory. Missing access fails the preflight before creating any news. Do not ask a colleague to install Node, Python or PG packages. Codex uses its runtime and the existing server dependencies. Do not copy production DATABASE_URL or passwords into this skill's local config.

The remote host reads only the selected website container environment, verifies its retired CloudBase environment (not used) matches local configuration, and requires all three collections' dual-write switches plus guard protocol v1. It runs the bundled `scripts/pg-sync-runtime.cjs` on the server. That bundle vendors the Website guard-aware reconciler, projections and task store from commit c4aa103; the older worker image is used only for Node and dependencies, never its older synchronization implementation.

## PG-only CMS ingestion

retired CloudBase credentials (not required) are no longer used. Configure `pg_primary.ssh_host` (default qcloud-CD) and `pg_primary.service` (default levelread-levelreadwebsite-2jbjx9). Use an already authorized SSH host; PG credentials stay inside the service container. COS credentials remain required for assets.
