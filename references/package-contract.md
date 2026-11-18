# Package Contract

`news-complete.json` has a professional top-level `title`, a compact `summary`, and exactly three levels in order 1, 2, 3.

- Title: aim for 6–8 words; never exceed 10, but prefer a compelling, clear fact over a word-count target. Lead with the most interesting verified part of the core event: an unusual action, vivid change, surprising contrast, meaningful scale, consequence, or human stake. State what happened in familiar ESL words. Keep a mechanism or approximate measurement when its combination with the event is the reason a reader would open the story; move only genuinely secondary details to the summary. Accuracy and intelligibility are hard gates, never excuses for clickbait or an empty teaser.
- Summary: one compact sentence of 2–15 words. It must extend the title with the key fact, rather than repeat it or become a second lead paragraph.
- Level 1: 100–120 words in 2–3 short paragraphs, 3 vocabulary items, 1 quiz.
- Level 2: 150–180 words in 3–4 paragraphs, 4 vocabulary items, 2 quizzes.
- Level 3: 180–220 words in 3–4 paragraphs, 5 vocabulary items, 3 quizzes.

## Reading-level calibration

Write all learner-facing English—headline, summary, article, vocabulary explanations, questions, and options—for the intended reader. Level 1 serves A1–A2, Level 2 serves B1–B2, and Level 3 serves C1–C2. Keep the same verified event and material caveats at every level; raise linguistic and analytical complexity, not factual accuracy.

- **Level 1 (A1–A2):** Make the event understandable on a first read by an elementary learner. Use familiar, concrete words and short, mostly simple sentences (often about 6–12 words). Put one new idea in each sentence, name the subject instead of relying on unclear pronouns, and explain any unavoidable new term immediately in simple English. Prefer direct time order and common verbs. Avoid passive chains, nested clauses, figurative wording, abstract summaries, and clusters of unfamiliar names or numbers. Do not invent a person's private motive to make the story sound warmer. Use the three vocabulary items to teach useful words, not to excuse an otherwise difficult passage. Before saving, read each sentence literally: replace a metaphor such as “the bear holds a piece of school life” with the direct fact “the bear helps the family remember school days.” If understanding the main event requires outside knowledge or repeated rereading, rewrite it.
- **Level 2 (B1–B2):** Use natural intermediate English. Add reasons, comparisons, and context with clear links between ideas. Some longer sentences and less common words are fine when their meaning is supported nearby. The reader should follow the event and its qualification without specialist knowledge.
- **Level 3 (C1–C2):** Use fluent, nuanced English. Add relevant implications, competing explanations, or limits supported by the sources. More complex syntax is welcome when it improves precision; avoid needless jargon and inflated prose.

Check the difficulty of quiz questions, options, and vocabulary explanations separately from the article. For Level 1, make the single quiz a quick check of **one idea**. Ask one short, direct question and give three short answers with parallel wording. Do not join two questions with “and,” or make the learner compare two long statements in each option. If the news has both an event and an important limit, keep both in the reading, then choose the single most important thing to test. The correct answer can express a sequence or a qualification in simple words, but should not become a miniature summary of the whole article.

Separate paragraphs with one blank line (`\n\n`). A level must never be delivered as one unbroken block of text.

Each vocabulary item is one word, appears verbatim in its level content, and has an English learner-facing explanation. Each quiz contains exactly three distinct, complete, standalone `options` and an `answer` string of `"1"`, `"2"`, or `"3"`. The correct option may paraphrase the reading in level-appropriate language. Its meaning must be directly and unambiguously supported by the current level alone, factually correct, and easy to identify after one careful read. The other two options should be simple plausible misunderstandings, not traps based on tiny wording differences or facts from another level. Across the six quizzes, answer positions are randomized after generation: every position is used, no position is used more than three times, and no three consecutive answers match. Reordering must preserve the correct option text.

## Editorial quality

### Headline reader interest, core, clarity, and fidelity

Before writing the title, state the story's **core in ordinary words**: who or what is changing, and what is happening. Identify which verified part of that core would make a reader stop scrolling and want to know more. Then note any qualification needed to avoid a misleading statement. A safe generic topic label is not enough; the title should contain the story's distinctive action, change, contrast, scale, consequence, or human stake.

Draft three genuinely different concise angles on the same verified core before choosing. For each, write (a) a one-sentence paraphrase of what a reader understands without the article and (b) the specific question or curiosity that would make that reader click. If a candidate's only attraction is a vague mystery, reject it. If its meaning needs the article to explain a name, phrase, or technical idea, rewrite it. Do not rescue an unclear or dull headline by explaining it in the rationale.

Use the most compelling part of the core event as the headline's anchor. Prefer common nouns and direct verbs; avoid abstract noun phrases, stacked modifiers, and jargon. Audit every proper noun and specialist phrase, not just the overall sentence. If a name only identifies where the story happened, replace it with the accurate familiar category (such as “an island,” “a country,” or “a volcano”) and put the name in the summary. Keep a proper noun only if it is broadly recognizable to the intended reader or the identity itself is central to the news. Keep a technical term only when it is the core concept readers need to learn; explain it in plain words around it. A familiar substitute must not change a factual property: for example, use “banknotes” rather than “paper money” if the actual notes are made of polymer. A number belongs in the headline when it makes a verified action or contrast unusually vivid and is immediately understandable; preserve “about” or another qualifier for an estimate. Do not keep an incidental number merely because it is large.

Do not lead with “a study,” “a model,” “researchers,” or a source organization when the main news is the real-world subject or change being studied. Name the phenomenon first; put the research method or attribution in the summary or article unless the research result itself is the core news.

Use a question headline when the question itself expresses the story's core and the article answers it directly. Do not force a question for a concrete event that reads more clearly as a statement. Curiosity should arise from a specific true fact in the title, not from withholding the event. Keep uncertainty and limits in view. Preserve material qualifiers such as “about,” “may,” or “the study estimates” when a number or claim in the headline is approximate or model-based. A short title must not make an estimate sound exact or a possible effect sound certain.

Examples:

- For an explainer about acrylamide in browned food, `Should You Avoid Eating Burnt Food?` names the familiar subject and the question the article answers. The summary can explain that the human cancer risk remains unclear.
- For a report that an Indonesian volcano added about 32.8 hectares after an eruption, prefer `A Volcano Makes Its Island Bigger` over a headline led by `Anak Krakatau` or the exact area. The island growing is the core concept; the unfamiliar name and measurement are supporting details.
- For a story about languages disappearing and a historical model, `Why Are So Many Languages Disappearing?` keeps the familiar core concept visible. Do not replace it with a lead about the model, empires, or the more abstract phrase language diversity.
- For a story whose point is that giant tortoises outnumber people across the Seychelles, `Seychelles Has More Giant Tortoises Than People` makes the comparison clear but assumes readers know an obscure place name. Prefer a scope-accurate plain category such as `One Country Has More Giant Tortoises Than People`; move the place name to the summary. Do not change the geographic scope just to avoid the name—for example, do not say “an island” if the report describes the whole country.
- For a chemistry story about controlling which mirror-image form of a molecule is made, `Chemists Learn to Choose a Molecule’s Mirror Form` relies on a specialist phrase. Prefer a plain explanation such as `Chemists Can Choose Which Form of a Molecule to Make`, if that accurately describes the result. Keep `molecule` only if it is the story's actual subject; do not preserve `mirror form` just because it is technically precise.
- For explorers using snowkites to cross about 1,700 kilometres of Greenland ice while gathering data, `Explorer Crosses Greenland Ice for Science` is accurate but hides the exceptional method and scale. Prefer `Kites Pull Explorers About 1,700 Kilometres Across Ice`: familiar words carry the hook, `about` preserves the estimate, and the summary can name Greenland and the scientific purpose. Do not imply a solo crossing if it was a team effort.

Before saving `news-complete.json`, check the title in this order. Accuracy is required at every step; the order ranks what to optimize among accurate candidates:

1. **Reason to open:** Does the title reveal the most interesting verified fact? What concrete question will a cold reader want answered after seeing it?
2. **Core and fidelity:** Does it state the main subject and action accurately, with material qualifiers, without exaggerating or withholding the event?
3. **Learner clarity:** Can an ESL reader paraphrase the event from the title alone, without the article or a glossary? Did you inspect every unfamiliar proper noun, technical phrase, and abstract term?
4. **Distinctiveness:** Would this title still fit dozens of other stories? If so, restore a meaningful mechanism, scale, contrast, consequence, or human detail.
5. **Conciseness:** Can any word be removed without weakening the hook or the core?

If a reader would need an explanation for a word or phrase in the title, replace it with a familiar description unless that term itself is the central news. Put omitted detail in the summary. The final rationale must identify the hook, the question it invites, a plain-language paraphrase, and any unfamiliar detail deliberately retained.

Do not replace the specific core event with a broad topic label. A question headline must name its familiar subject or condition and the article must genuinely answer it. Do not turn a nuanced reported question into a universal claim.

Examples of direct headlines (illustrative only; check each against its own source):

- `A New Plan Could Transform Urban Night Travel` → `Two Cities Get a New Night Train`
- `Major Scientific Breakthrough in Ocean Conservation` → `New Ocean Park Will Protect Sea Life`
- `Is Eight Hours Essential?` → `Do Adults Need Eight Hours of Sleep?`

Use the short summary to add one important fact that did not fit in the headline.

Keep the fact, its limits, and the lesson distinct. When a headline compares two things under different conditions, say what the number shows and what it does *not* establish at every level. Do not let a catchy headline turn a qualified claim into an unconditional one.

Make Level 1 genuinely accessible: prefer common words and short sentences, explain any necessary technical term in context, and reserve abstract analysis for higher levels. Progress from the concrete event in Level 1 to comparison and interpretation in Levels 2 and 3.

Questions should test the story's central learning point rather than only a memorable number. If a qualification or caveat is the main lesson, Level 1's single question can test that caveat by itself in simple language. Use two reasonable alternatives drawn from likely misunderstandings, but do not make the reader solve a subtle logic puzzle. Each option must read as a complete answer to the question by itself; avoid fragments beginning with words such as “and” or “because” that depend on hidden surrounding text.

### Blind quiz review before production

Generate `blind-quiz.json` with `review-sheet`. It includes title, summary, each level's reading, questions, and options, but no answer keys. Review this sheet without opening the keyed draft. For each question, choose an option by its **exact text**, quote a short evidence phrase from that level, and explain how the evidence supports the answer's meaning, including when the answer is a paraphrase. Give a separate reason for rejecting each other option to confirm there is exactly one correct answer. If the question, any option, or the key is wrong, repair `news-complete.json`, regenerate the sheet, and repeat the review. Do not merely approve a phrase because it appears in the reading.

Write `editorial-review.json` using the sheet's fingerprint and this shape:

```json
{
  "fingerprint": "SHA-256 value copied from blind-quiz.json",
  "headline": {
    "inviting": true,
    "simple": true,
    "clear": true,
    "faithful": true,
    "hookFact": "The verified action, contrast, scale, consequence, or human detail that makes this story worth opening",
    "readerQuestion": "A specific question a cold reader would want the article to answer",
    "readerParaphrase": "What an ESL reader can understand from the headline alone",
    "termChecks": [
      {"term": "Anak Krakatau", "decision": "omit", "plainAlternative": "a volcano"}
    ],
    "rationale": "Explain why this true hook is more inviting than the safe generic alternative while remaining accurate and understandable"
  },
  "quizzes": [
    {"id": "L1Q1", "selectedOption": "Exact option text", "evidence": "Exact phrase from Level 1", "rationale": "Why it answers the full question", "rejectedOptions": [{"option": "Exact other option", "reason": "Why it is wrong"}, {"option": "Exact third option", "reason": "Why it is wrong"}], "answerFitsQuestion": true, "onlyOneCorrect": true, "optionsStandAlone": true}
  ]
}
```

Include all six decisions in level and question order: `L1Q1`, `L2Q1`, `L2Q2`, `L3Q1`, `L3Q2`, `L3Q3`. Set an approval to `true` only after checking it. Approve `inviting` only when `hookFact` is both verified and present in the title and `readerQuestion` describes real curiosity rather than an empty tease. In `termChecks`, list every potentially unfamiliar proper noun, specialist phrase, or abstract term in the headline. Use `decision: "omit"` with a plain alternative for details removed; use `decision: "keep_core"` only when the term itself is the story's core and the article teaches it; use `decision: "keep_familiar"` only for a name readers are likely to recognize. If none need review, use an empty list. A nonempty list is not a reason to keep a term: the final title must still pass the headline-only paraphrase test. `produce` checks the existing simple, clear, faithful review fields before any audio generation or upload; the new reader-interest fields require editorial judgment and are not mechanically scored. The fingerprint covers title, summary, reading text, questions, and option wording while allowing the publisher's option shuffle. `review-check` checks the final `news-package.json` after the shuffle. These program checks enforce completeness, evidence text, and key agreement; the actual meaning, clarity, uniqueness, and appeal require the editorial reasoning above.

Before calling `produce`, self-check all of the constraints above. The bundled validator treats metadata length, word count, paragraph count, vocabulary presence, answer-position distribution, and editorial-review agreement as blocking errors. The editorial review checks whether a paraphrased answer is actually supported by the current reading.

`news-package.json` adds `titleid`, uploaded `cover`, uploaded level `audio` URLs, millisecond `date`, `originalUrl`, `public: false`, and `readCount: 0`.

## Title localization before CMS ingest

Before an explicit CMS ingest, Codex must create `title-translations.json` beside `news-package.json`. It must contain the final English `title`, matching `titleid`, and one concise, native-language news headline for each of the six target API language codes: `zh-CN` (Simplified Chinese), `zh-TW` (Traditional Chinese), `ja` (Japanese), `ru` (Russian), `es` (Spanish), and `pt-BR` (Brazilian Portuguese).

Translate the **final English headline itself**, not the article, summary, or fact brief. Use natural headline wording in each language while preserving the English title’s subject, action, purpose, scope, and uncertainty. A name, number, location, motivation, award, or outcome that appears only in the article must not be introduced into a translated title. Do not replace a generic phrase in the English title with a more specific fact from the body, even when that fact is true. Do not turn an intended result (such as “to see more stars”) into a different claim (such as “protecting the night sky”). If a detail would improve all titles, revise the English title first and then retranslate all six.

Review each target title by back-translating it into English without looking at the article. Compare that reading against the final English title and fix any added, missing, or changed meaning. Check the Chinese titles separately for natural, concise wording. For example, “A City in Taiwan Changes Lights to See More Stars” can become “台湾一座城市调整照明，让人们看见更多星星”; “台湾桃园调整路灯，守护拉拉山星空” fails because it adds names and changes the purpose. Do not add explanations, quotes, or a trailing full stop. The publisher blocks ingest unless the six-code set is complete and each translation artifact matches the final English package title exactly; this structural check cannot judge semantic equivalence, so the back-translation review is required.


## Produced timing fields

The source readings object need not contain media fields. Normal production adds `audio` and `audioTiming` to each of its three Levels only after validation and COS byte readback. `audioTiming` is schemaVersion 1 and contains `timelineUrl`, `timelineSha256`, `contentSha256`, `audioSha256`, `audioUrl` and integer `durationMs`; `audioUrl` must equal that Level's `audio`, and its content hash binds the exact unnormalized English text. Do not carry a previous reference through an edit to English text or audio. The timeline JSON stores English UTF-16 original character offsets and integer millisecond cues. See [alignment and verification](audio-alignment.md) for artifact retention and failed/resumed production behavior.
