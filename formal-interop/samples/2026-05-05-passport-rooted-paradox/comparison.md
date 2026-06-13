# Formal Output Comparison

Source: `external/blog-pro/src/content/argmaps/2026-05-05-passport-rooted-paradox.yaml`

## 1. Argdown

File: `argument.argdown`

Effect:

- Best at preserving the article as a public argument map.
- Support and attack edges remain readable without explaining the whole internal YAML schema.
- Strong fit for publication, external review, and later SVG / web-component export.

Cost:

- It does not reason by itself. It shows argument structure; it does not tell us which conclusion is warranted after rebuttals.
- Formal formulas become annotations, not machine-checked propositions.

Best role:

Public interchange and visualization layer.

## 2. DeLP-Style Rules

Active file: none. DeLP is parked as a future research-lab option.

Effect:

- Best at representing defeasible claims.
- It captures the civic-proof pattern where a default is useful but defeatable:
  - passport roots are normally useful because coverage is high;
  - passport roots become insufficient when issuer-adversary overlap is present;
  - zkPassport solves privacy but does not defeat issuer-side revocation;
  - ICAO robustness helps against forgery but not against legitimate issuer weaponization.

Cost:

- Requires a runner / exact dialect choice before it can be called executable.
- Predicate naming becomes its own ontology work.
- Public readers will need an explanation layer.

Best role:

Research-lab stress test for objections, exceptions, and context-sensitive conclusions.

## 3. Lean 4

Active file: none. Lean is parked as a future lemma-library option.

Effect:

- Best at isolating the minimal reusable theorem shape.
- The sample proves that, after accepting the SRP axiom, single-passport-root validity fails under issuer-adversary overlap.
- It also shows how R2/R3/R4 can witness `MultiRootedAvailable` when trust and non-compromise are supplied.

Cost:

- It cannot establish empirical premises. Lean will not prove that Turkey 2016, Belarus 2023, or Russia 2022 are issuer-adversary cases unless those facts are encoded or assumed.
- Whole-article Lean formalization would be too slow and may create false precision.

Best role:

Small reusable lemma library for recurring civic-proof logical forms.

## Decision

Keep `argmap.yaml` as canonical internal data.

Use Argdown export first as the publication and external-collaboration exchange format.

Park DeLP as a prototype. Revisit it only if rebuttal / exception reasoning becomes a concrete blocker.

Park Lean as a prototype. Revisit it only for recurring formal skeletons such as:

- `issuer_adversary + sovereign_root -> not trust_satisfied`
- `T valid iff T1 and T2 and T3`
- `multi_root_available iff exists noncompromised accepted root`
- `deployment_valid iff all boundary conditions hold`
