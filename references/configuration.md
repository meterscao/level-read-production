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
