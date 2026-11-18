# Level Read Production

Codex produces three graded English readings, a cover, audio, COS uploads, six localized titles and six article translations, and optional unpublished PostgreSQL ingestion. Content generation and asset uploads are independent of insertion.

Private configuration: `~/.codex/level-read-production/config.json`. See [references/configuration.md](references/configuration.md). AI and COS credentials support media production. The SSH bridge runs the PG runtime in the approved Website container; database credentials remain there. The bridge uses SSH host-key verification and the shared PostgreSQL runtime uses verified TLS.

English is the source. The default targets for both translation files are `zh-CN`, `zh-TW`, `ja`, `ru`, `es`, and `pt-BR`, matching the Web and Client API. See [historical translation rules](references/body-translations.md#historical-packages) for original-package inspection and retries.

Archive: `~/Documents/Level Read Production/YYYY-MM-DD-titleid/`. Editorial checks bind to final wording. A PG transaction inserts the news and twelve translations. Inspect repeated packages first. Deterministic IDs and content digests support unchanged retries; conflicts never overwrite another story. Incomplete receipts remain resumable.

Local regression checks, with no production access:

```bash
python3 -m unittest discover -s . -p 'test*.py'
python3 -m unittest discover -s test -p 'test*.py'
node scripts/check-pg-primary-provenance.cjs
node test_pg_runtime.cjs
node test-pg-inspect.cjs scripts/pg-primary-runtime.cjs
```

Use `python3 scripts/publisher.py validate --input news-package.json` for offline structural checks; supply the review and translation paths for complete artifact checks. This command does not load credentials or modify files.

See [SKILL.md](SKILL.md) for workflow routing and [references/commands.md](references/commands.md) for production commands and [references/pg-ingest-troubleshooting.md](references/pg-ingest-troubleshooting.md) for PG diagnostics.

## Development from the source repository

The publisher orchestration and local validation use Python's standard library. Forced alignment for production uses FFmpeg, the separate Python environment in [alignment-environment.freeze.txt](resources/alignment-environment.freeze.txt), and hash-verified local acoustic and English Punkt data. See [audio alignment](references/audio-alignment.md) for the local paths. PG ingest runs the bundled CommonJS runtime with Node and `pg` in the approved Website container.

Regenerate the PG runtime and isolated schema from the immutable Website commit recorded in [PG provenance](scripts/pg-primary-provenance.json). Use Node 22 and esbuild 0.27.2. The Website Git checkout must contain the original commit object.

```bash
ESBUILD_PATH=/absolute/path/to/esbuild node scripts/build-pg-primary.cjs /absolute/path/to/website-git-checkout
git diff --exit-code -- scripts/pg-primary-runtime.cjs scripts/pg-primary-provenance.json test/primary-schema.sql
```

Run the source repository's integration tests with PostgreSQL 16 tools on `PATH`, Node 22, and `pg@8.16.3` available to Node. The runner creates and stops a temporary PostgreSQL cluster on a Unix socket.

```bash
node scripts/test-pg-primary-local.cjs
```
