# Word timelines in production and local alignment

Default news production includes local forced alignment and hash-bound COS timelines. An expressly local alignment/checkpoint request remains limited to local files and does not authorize uploads, ingest or deployment.

## Existing news

Run `publisher.py align-audio --input <local news-package.json> --output <separate directory> --resume`. The input archive is read-only. Audio files must be local and named `<titleid>-level-1.mp3` through level 3; `--audio-dir` and repeated `--level` arguments narrow the source/scope. No private configuration is loaded, no TTS is called and no database is contacted.

The command writes per-level `sample.mp3`, original `transcript.txt`, `sample.json`, `alignment.raw.json`, standard `timeline.json`, and `quality.json`. The output root contains `alignment-manifest.json`, `batch-metrics.json` and an offline `index.html` listening page. Keep its relative audio directories together when sharing the local bundle.

## Default production and optional checkpoint

Normal `produce` preflights the pinned runtime before any TTS charge. It generates local MP3s, aligns all three levels, and checks their exact UTF-16 word ranges, title/level identity, content/audio/timeline hashes, cue ordering and decoded-media duration before the first COS write. The final package contains `levels[].audio` and `levels[].audioTiming`.

MP3 and JSON keys include their byte hashes. Uploads use `x-cos-forbid-overwrite`; an existing object is reused only after complete signed and public byte readback. The configured bucket must never have enabled versioning. Public readback verifies CORS for `https://levelread.com` and `http://127.0.0.1:3130`; the publisher never expands bucket CORS or permissions. Missing CORS is an explicit failure. Receipts record completed object hashes and actual stage. On an unchanged-input `--resume`, local alignments are revalidated and existing COS objects are freshly verified; completed filenames and saved checkpoints alone are insufficient.

`produce --align-audio` is the explicit local listening checkpoint. It still returns `audio_alignment_review_required` after alignment, **before the first upload**. Alignment failure preserves local MP3s and records `audio_alignment_failed`. A local checkpoint is not a complete produced package. Standalone `align-audio` neither loads private configuration nor calls TTS/COS/PG.

Default production stops on a missing runtime, failed alignment, stale source, invalid timeline, upload conflict or failed readback; it cannot silently finish without timelines. Preserve original completed ingest receipts. If a story is already ingested, use the separately authorized existing-news timing migration rather than regenerating/re-ingesting the package.

For new ingest, keep the entire story directory. The publisher rechecks local references/files and freshly verifies signed/public COS bytes before its usual unpublished 13-record PG transaction. Legacy `inspect` remains available without new timing. An existing failed PostgreSQL receipt for a pre-upgrade package can retry its unchanged legacy request/digest; a new `timingRequired` package cannot use that exception. Successful structural/transport checks do not fabricate a CMS reviewer or assert a measured human synchronization tolerance.

## Runtime

WhisperX 3.8.6 and PyTorch 2.8.0 run in a separate Python 3.11 environment, outside Website and system Python dependencies. FFmpeg must be available. The alignment-only dependency snapshot is `resources/alignment-environment.freeze.txt`. Use the pinned model `WAV2VEC2_ASR_BASE_960H`, which the worker verifies by SHA-256 before loading.

Provision the four English Punkt files listed in [the checksum manifest](../resources/punkt-english/provenance.json) in `~/.codex/level-read-production/alignment-runtime/nltk_data/tokenizers/punkt_tab/english/`. Use an existing verified local `punkt_tab/english` directory or extract those four files from a local `punkt_tab.zip` that matches the manifest's archive SHA-256. Set `LEVEL_READ_PUNKT_DIR` to use another local directory containing the four files. The repository carries only the checksum manifest. The preflight verifies every file before TTS or alignment, and the worker checks again before loading it. Missing or changed files stop the run without network downloads.

Codex manages the runtime under `~/.codex/level-read-production/alignment-runtime/`; do not ask a colleague to install or paste commands. Avoid automatic runtime upgrades or network model downloads during production. A missing model/runtime is an explicit local error, never permission to use a cloud fallback.

## Output and review

Standard JSON is schemaVersion 1, English, UTF-16 original character ranges and integer milliseconds. `en-display-v1` uses whitespace-delimited occurrences, trims outer punctuation and keeps internal apostrophes, numeric separators and hyphens; gaps are reconstructed from original text. Curly quotes/dashes and whitespace are normalized one-for-one only for acoustic input; source text/hash remains unchanged. Python offsets are explicitly converted to UTF-16, including astral characters. Pure punctuation chunks are not display-word tokens.

No interpolation or average-duration timestamps are generated. Unmapped text, overlapping/zero/invalid intervals, wrong hashes and malformed token IDs fail validation. An unaligned word may remain without a cue and must be reported. Existing output is reused only when input/pipeline/output hashes and structural validation still match; file existence is insufficient.

Quality reports retain `review_required` as acoustic diagnostics, including during the authorized default production path; this label does not create or require a website administrator session. It is not a claimed human approval. Coverage and model scores are diagnostics, not synchronization accuracy. The listening page shows low-score/numeric risk tokens, supports sample switching, seek and speed, and can export a hash-bound manual listening record; it never approves online attachment. Review dates, numbers, proper nouns, short words and sentence/paragraph boundaries. Forced alignment cannot prove TTS spoke every original word.

Report structural checks, playback checks and human listening measurements separately. Do not claim a 150ms error target passed without independent human timing references. Preserve original archives, raw outputs and failure reports. For a local-only request, supply the listening page and sample summary. Default production may populate verified timing fields as described above. Never change historical ingest receipts/digests or describe structural checks as manual listening approval.
