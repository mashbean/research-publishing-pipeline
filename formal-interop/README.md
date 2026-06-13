# Formal Interop Prototype

This folder tests whether civic-proof argument maps should export into formal or semi-formal reasoning languages.

Current source of truth remains the existing `argmap.yaml` produced by the research article pipeline. These files are comparison artifacts, not replacements for the article, fact-check report, or blog-pro argument map.

## Current Decision

Use Argdown first. DeLP-style rules and Lean 4 remain parked research prototypes and are not part of the pipeline.

Pipeline rule:

1. The argmap pass produces `final/argmap.yaml`.
2. `scripts/generate_argdown.py` deterministically converts it to `final/argument.argdown`.
3. `scripts/render_argdown_assets.py` renders static HTML/SVG assets from `argument.argdown`.
4. `argument.argdown` must not introduce new claims, rewrite article text, or become a second source of truth.
5. The export sanitizes body text into Argdown parser-safe prose. Full formulas and rich text remain in `argmap.yaml`.

## Validation

If Argdown CLI is available:

```bash
python3 ../scripts/validate_argdown.py --input samples/2026-05-05-passport-rooted-paradox/argument.argdown
python3 ../scripts/render_argdown_assets.py --input samples/2026-05-05-passport-rooted-paradox/argument.argdown --output-dir /tmp/argdown-render
argdown json "samples/*/argument.argdown" /tmp/argdown-json --throwExceptions
```

The current phase validates syntax, exportability, and static rendering. blog-pro reads source files from
`src/content/argdowns/<slug>.argdown` and embeds rendered assets from `public/argdown/<slug>/`.

## Current Sample

- Source argmap: `external/blog-pro/src/content/argmaps/2026-05-05-passport-rooted-paradox.yaml`
- Source article: `tools/research-publishing-pipeline/jobs/2026-05-05-passport-rooted-paradox/final/article-final.md`
- Sample folder: `samples/2026-05-05-passport-rooted-paradox/`

## Candidate Outputs

| Format | Role | What To Evaluate |
|---|---|---|
| Argdown | Public argument-map exchange format | Can readers follow support / attack relations without learning the whole pipeline? |
| DeLP-style rules | Parked research prototype | Useful for future rebuttal stress tests, not pipeline output. |
| Lean 4 | Parked research prototype | Useful for future lemma sketches, not whole-article formalization. |

## Decision Rule

Keep a format only if it does one job better than `argmap.yaml`.

- Keep Argdown if it improves external readability and exportability.
- Revisit DeLP only if rebuttal / exception handling becomes a concrete blocker.
- Revisit Lean only for a small library of recurring civic-proof lemmas, not for whole-article formalization.
