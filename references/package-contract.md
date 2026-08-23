# Package Contract

`news-complete.json` has `title`, `summary`, and exactly three levels in order 1, 2, 3.

- Level 1: 90–140 words, 3 vocabulary items, 1 quiz.
- Level 2: 130–210 words, 4 vocabulary items, 2 quizzes.
- Level 3: 180–290 words, 5 vocabulary items, 3 quizzes.

Each vocabulary item has a `word` appearing in its level content and an English `explanation`. Each quiz contains exactly three distinct `options` and an `answer` string of `"1"`, `"2"`, or `"3"`. Across the six quizzes, every answer position is used, no position is used more than three times, and no three consecutive answers match.

## Editorial quality

Keep the fact, its limits, and the lesson distinct. When a headline compares two things under different conditions, say what the number shows and what it does *not* establish at every level. Do not let a catchy headline turn a qualified claim into an unconditional one.

Make Level 1 genuinely accessible: prefer common words and short sentences, explain any necessary technical term in context, and reserve abstract analysis for higher levels. Progress from the concrete event in Level 1 to comparison and interpretation in Levels 2 and 3.

Questions should test the story's central learning point rather than only a memorable number. In a story whose key point is a qualification or caveat, Level 1's single question should test that caveat. Use plausible alternatives drawn from likely misunderstandings; avoid distractors that are obviously unrelated or plainly false.

`news-package.json` adds `titleid`, uploaded `cover`, uploaded level `audio` URLs, millisecond `date`, `originalUrl`, `public: false`, and `readCount: 0`.
