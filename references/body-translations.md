# Body translations for CMS ingest

Before a requested CMS ingest, translate the final package into `zh-CN`, `zh-TW`, `ja`, `ko`, `es`, and `pt-BR` and save `body-translations.json` beside `news-package.json`. Use the title translations reviewed for direct equivalence with the final English title exactly; do not derive new titles from the translated bodies. Translate the summary and each level's article content faithfully, preserving the source's paragraph boundaries, names, numbers, attribution, and uncertainty. Do not simplify, expand, or add facts. A level title is translated only when the English level has one; otherwise use an empty string. Review each language for natural wording and compare every translated paragraph with its English source. Quiz text and vocabulary explanations remain in English in the current reader; the existing `enli_news_translation` schema contains article text, not translated quizzes.

Run `python3 scripts/publisher.py translation-fingerprint --input /absolute/path/news-package.json` to get the `sourceFingerprint` that binds this artifact to the final package. Do not copy a hash from another story. The file shape is:

```json
{
  "titleid": "story-title",
  "sourceFingerprint": "sha256-of-final-source-fields",
  "translations": [
    {
      "languageCode": "zh-CN",
      "title": "与 title-translations.json 完全相同的标题",
      "summary": "摘要译文",
      "levels": [
        {"level": 1, "title": "", "content": "第一段译文\n\n第二段译文"},
        {"level": 2, "title": "", "content": "第一段译文\n\n第二段译文\n\n第三段译文"},
        {"level": 3, "title": "", "content": "第一段译文\n\n第二段译文\n\n第三段译文"}
      ]
    }
  ]
}
```

The example shows one language; the real file must contain all six exactly once. The publisher validates the language set, title match, source fingerprint, level order, and paragraph counts **before** creating a CMS news record. It writes six records to `enli_news_translation`, linked by the returned `newsId`. Each record contains `newsId`, `languageCode`, translated `title`, `summary`, and `levels`. The schema also requires each level's `vocabulary` explanations; the publisher copies the original English explanations, matching the website's current translation behavior.
