# Level Read Production

Codex produces three graded English readings, a cover, audio, COS uploads, six localized titles and article translations, and optional unpublished PostgreSQL ingestion. Content generation and asset uploads are independent of insertion.

Private configuration: `~/.codex/level-read-production/config.json`. See [references/configuration.md](references/configuration.md). AI and COS credentials support media production. The SSH bridge runs the PG runtime in the approved Website container; database credentials remain there. Host-key verification, verified TLS and database authority checks are required.

Archive: `~/Documents/Level Read Production/YYYY-MM-DD-titleid/`. Editorial checks bind to final wording. A PG transaction inserts the news and twelve translations. Inspect repeated packages first. Deterministic IDs and content digests support unchanged retries; conflicts never overwrite another story. Incomplete receipts remain resumable.

Local regression checks, with no production access:

```bash
python3 -m unittest discover -s . -p 'test*.py'
node test_pg_runtime.cjs
```

Use `python3 scripts/publisher.py validate --input news-package.json` for offline structural checks; supply the review and translation paths for complete artifact checks. This command does not load credentials or modify files.

See [SKILL.md](SKILL.md) for workflow routing and [references/commands.md](references/commands.md) for production commands and [references/pg-ingest-troubleshooting.md](references/pg-ingest-troubleshooting.md) for PG diagnostics.
