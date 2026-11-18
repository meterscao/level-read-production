# Revise the current story without rebuilding everything

Use the existing `titleid`, archive and assets. An explicit replacement title is the title to use, not a prompt to propose alternatives. Keep published records outside this local revision workflow; a new `ingest` is not an update operation.

## Title only

Update the title in the local source/package and readable preview. Evaluate the revised headline for fidelity, update its editorial rationale and fingerprint, and retain unchanged quiz decisions only because their readings/questions/options are unchanged. Existing title/body translations tied to the previous title are stale: regenerate them before a later ingest, or mark them stale rather than silently certifying them. Do not change body text, cover, audio or the stable titleid merely because the headline changed.

## Cover only

Use the image tool and the user's reference/direction. Inspect and export a new versioned 1500 × 900 sRGB PNG, keeping the prior image recoverable. Upload only that approved image when the user's requested scope includes replacing production assets; update the package cover URL, cover-upload metadata and state consistently. Reuse existing audio URLs and article wording. The publisher's `cos_upload` helper may be used for this single-asset operation; `produce --resume` is not an editing command and can reuse the old cover URL.

## Reading changes

Revise only the requested levels/fields. Regenerate affected quizzes/reviews, translations and audio when their source changes; preserve unaffected assets. Never approve an obsolete fingerprint merely to pass validation. Re-run local `validate` before production or ingest.

A local change to an already-ingested package does not update PG. Report that state accurately and use a separately supported authorized update path; do not insert a duplicate or overwrite a published record.
