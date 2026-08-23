# Package Contract

`news-complete.json` has `title`, `summary`, and exactly three levels in order 1, 2, 3.

- Level 1: 90–140 words, 3 vocabulary items, 1 quiz.
- Level 2: 130–210 words, 4 vocabulary items, 2 quizzes.
- Level 3: 180–290 words, 5 vocabulary items, 3 quizzes.

Each vocabulary item has a `word` appearing in its level content and an English `explanation`. Each quiz contains exactly three distinct `options` and an `answer` string of `"1"`, `"2"`, or `"3"`. Across the six quizzes, every answer position is used, no position is used more than three times, and no three consecutive answers match.

`news-package.json` adds `titleid`, uploaded `cover`, uploaded level `audio` URLs, millisecond `date`, `originalUrl`, `public: false`, and `readCount: 0`.

