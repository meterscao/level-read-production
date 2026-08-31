# Package Contract

`news-complete.json` has a professional top-level `title`, a compact `summary`, and exactly three levels in order 1, 2, 3.

- Title: at most 10 words. Write a clear, factual, editorial headline that is concise and inviting; do not use clickbait, vague teasers, or unsupported claims.
- Summary: one compact sentence of 2–15 words. It must extend the title with the key fact, rather than repeat it or become a second lead paragraph.
- Level 1: 100–120 words in 2–3 short paragraphs, 3 vocabulary items, 1 quiz.
- Level 2: 150–180 words in 3–4 paragraphs, 4 vocabulary items, 2 quizzes.
- Level 3: 180–220 words in 3–4 paragraphs, 5 vocabulary items, 3 quizzes.

Separate paragraphs with one blank line (`\n\n`). A level must never be delivered as one unbroken block of text.

Each vocabulary item is one word, appears verbatim in its level content, and has an English learner-facing explanation. Each quiz contains exactly three distinct `options` and an `answer` string of `"1"`, `"2"`, or `"3"`. The correct option must appear verbatim in the current level's content, so the question can be answered from that reading alone. Across the six quizzes, answer positions are randomized after generation: every position is used, no position is used more than three times, and no three consecutive answers match. Reordering must preserve the correct option text.

## Editorial quality

### Headline fidelity

Before writing the title, identify the news spine: **subject**, **event or claim**, and the **context that makes this report distinctive** (such as place, affected group, cause, comparison, or qualification). The title must retain the subject and event, plus that distinguishing context whenever leaving it out would change the story's meaning. Accuracy beats clever compression.

Do not replace a concrete report with a broad topic label. A title may use a question only if the original reporting is genuinely organized around that question; it must still name the relevant subject or condition. Do not turn a nuanced reported question into a universal claim.

Examples of faithful compression:

- `Young Brits Choose Japan` → `Young Britons Head to Japan as Yen Falls`
- `Is Eight Hours Essential?` → `Do Adults Need Eight Hours’ Sleep?`
- `Beyblade Battles Return` → `Hong Kong Adults Join Beyblade Revival`

Before saving `news-complete.json`, compare the title against the verified fact brief and confirm: every stated fact is supported; the main subject and event remain; and no qualifying context has been removed in a way that changes the claim. Use the short summary to add one important fact that did not fit in the headline.

Keep the fact, its limits, and the lesson distinct. When a headline compares two things under different conditions, say what the number shows and what it does *not* establish at every level. Do not let a catchy headline turn a qualified claim into an unconditional one.

Make Level 1 genuinely accessible: prefer common words and short sentences, explain any necessary technical term in context, and reserve abstract analysis for higher levels. Progress from the concrete event in Level 1 to comparison and interpretation in Levels 2 and 3.

Questions should test the story's central learning point rather than only a memorable number. In a story whose key point is a qualification or caveat, Level 1's single question should test that caveat. Use plausible alternatives drawn from likely misunderstandings; avoid distractors that are obviously unrelated or plainly false.

Before calling `produce`, self-check all of the constraints above. The bundled validator treats metadata length, word count, paragraph count, vocabulary presence, quiz answer evidence, and answer-position distribution as blocking errors.

`news-package.json` adds `titleid`, uploaded `cover`, uploaded level `audio` URLs, millisecond `date`, `originalUrl`, `public: false`, and `readCount: 0`.

## Title localization before CMS ingest

Before an explicit CMS ingest, Codex must create `title-translations.json` beside `news-package.json`. It must contain the final English `title`, matching `titleid`, and one concise, native-language news headline for each exact API language code: `zh-CN` (Simplified Chinese), `zh-TW` (Traditional Chinese), `ja` (Japanese), `ko` (Korean), `es` (Spanish), and `pt-BR` (Brazilian Portuguese).

These are editorial localizations, not mechanical translations. Preserve the verified news spine—subject, event or claim, and material qualification—while using idiomatic headline style in each target language. Do not add explanations, quotes, unsupported claims, or a trailing full stop. The publisher blocks ingest unless the six-code set is complete and each translation artifact matches the final English package title exactly.
