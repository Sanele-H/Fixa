# Role 1: Language and translation

**You own** `backend/fixa/translation/` and `experiments/translation_test/`.

**Your part of the demo:** Nomsa's "R450, Tuesday 10:00" arrives on Mrs. van Wyk's phone in Afrikaans with the price and time exactly right, and "See original" shows the isiZulu.

## Already in place

| File | State |
|---|---|
| `translation/languages.py` | Language codes. Mark the pilot languages on Day 1. |
| `translation/backends/base.py` | The `TranslationBackend` interface every backend implements |
| `translation/backends/echo.py` | A fake backend (`[zu] text`) so everyone can work without API keys |
| `translation/backends/__init__.py` | Picks a backend by `TRANSLATION_BACKEND` in `.env`. Register new ones here. |
| `translation/token_protection.py` | `protect_tokens` / `restore_tokens`: **TODO** |
| `translation/glossary.py` + `data/glossary.csv` | CSV loading works; matching is **TODO**. 3 starter rows need a first-language check. |
| `translation/pipeline.py` | `TranslationResult` shape (Role 3 depends on it); `translate()` is **TODO** |
| `backend/tests/test_token_protection.py` | Your to-do list as tests |
| `experiments/translation_test/` | The CSV has 2 of 30 messages; the scoring functions are **TODO** |

## Your week

| Day | Deliverable |
|---|---|
| Sun 27 | Write the 30 test messages (see the translation test README). Get the first real backend call working in its own file under `backends/`. |
| Mon 28 | `protect_tokens` / `restore_tokens` pass the tests. Glossary matching works. `TranslationPipeline.translate` is wired up. |
| Tue 29 | Second backend. Run the 30-message test on both, with and without protection. Record the results. |
| Wed 30 | Pick the demo backend, set it in `.env`, and check it's fast enough for chat (about 2 s). |
| Thu 1 | One slide: what each backend broke, and how protection fixed it. |

## Decisions that are yours

- **Placeholder format.** Which format survives each backend (`[[0]]`, `<x0/>`, `__0__`…)? Test it; don't guess.
- **Glossary matching.** isiZulu adds prefixes that change with grammar (igiza → legiza), so the CSV notes suggest storing stems such as `-giza` for checking. Hints go to backends that can use them, like LLMs.
- **When to flag "unsure".** A lost protected value, a missing glossary term, or the backend saying it's unsure.
- **Caching.** The job list re-translates the same descriptions, so cache by (text, source, target).

## Contracts you must keep

- `TranslationPipeline.translate(text, source, target) -> TranslationResult` **never raises**. On failure it returns the original text with the `BACKEND_FAILED` flag, so chat keeps working.
- `[***]` (`fixa.domain.tokens.MASKED_CONTACT_TOKEN`) comes out exactly as it went in.
- API keys only go in `.env`.

## Notes on backends

- **Google Translate** supports af, zu, xh, st, tn and nso. The v2 REST API with an API key is the simplest option.
- **An LLM** can follow glossary hints and report when it's unsure. The `anthropic` SDK is already installed. If you use Claude, start with `claude-opus-5`, and check `stop_reason` before reading the reply.
- **Meta NLLB** uses codes like `zul_Latn`, `afr_Latn` and `nso_Latn`. Keep that mapping inside `nllb.py`.
- **Lelapa AI** is built for South African languages, so it's worth one test.

## Run your part

```bash
npm run test:api                                   # your tests go from xfailed to passed
npm run translation-test -- --backends echo,google
```
