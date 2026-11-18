# PostgreSQL ingest troubleshooting

Re-read the installed skill and run its current publisher by absolute path. Copied scripts or cached modules can be stale. `publisher.py --help` must expose `inspect`; `doctor` reports local configuration status and does not verify live connectivity.

Run `inspect` with the package, editorial review and both translation files before a repeated insertion:

- `missing`: insert only when authorized, using the normal PG transaction.
- `existing` with exact news/title/body matches and six READY titles for the inspected languages: report the physical PG ID without creating a duplicate. Additional cached languages are listed separately and count toward the stored total.
- Different, incomplete, ambiguous or published content: report the discrepancy without overwriting or deleting it.
- `unavailable`: check the approved SSH host/service and PG connectivity read-only. Keep host-key verification and TLS enabled, and never print credentials or container environment values.

An incomplete PG receipt is retried in place with the same four input files. The [historical translation rules](body-translations.md#historical-packages) describe when the original Korean set can be retried. A successful receipt prevents another insertion. Preserve unrecognized receipts for inspection; do not discard them to bypass a conflict.

If another ingest is in progress in the same story directory, wait for it to finish and inspect the receipt before retrying. The publisher serializes ingest attempts for each archive and writes receipts atomically.

After an insertion, inspect again and confirm one unpublished news record, six READY title translations and six body translations, all matching (13 records). Record the PG ID, backend and receipt path in `production-state.json`.
