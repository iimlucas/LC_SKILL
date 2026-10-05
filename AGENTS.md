# Repository guidance

## Future frontend changes: screenshot evidence

This repository currently has no maintained frontend page. That does not exempt
future UI work. Apply this section when adding/changing a web page, native GUI or
interactive terminal screen, including backend changes that alter its display
or behavior. Ordinary CLI text/prompts/tables, generated CSV/Excel documents and
non-rendered documentation need no screenshots; explain `N/A: no UI impact`.

For an applicable UI change:

- Commit a coverage checklist: affected page/entry, state/transition, steps,
  fixture/data, expected result, exact screenshot link and actual result. Assess
  normal/empty/loading/error/disabled and changed filter/expand/selection/dialog
  states. Capture each affected applicable state; explain unchanged or N/A
  categories. Cover affected shared-component
  consumers; explicitly list and justify equivalent representative grouping,
  subject to reviewer agreement that no distinct behavior is hidden.
  Capture wide/narrow supported sizes for layout changes, or explain fixed-size
  N/A. Do not require every page × state × data × viewport combination.
- Capture the actual final running implementation, not a mockup/editor preview.
  Record launch/build/runtime identity, platform, dimensions, safe fixture
  provenance and capture steps. Validate shipped-asset sync; label prototype,
  offscreen or mock-tool limits without claiming native/production proof.
- Bind captures to the tested product-code commit SHA. Before committing, record
  base SHA plus complete relevant tracked/untracked input hashes (source,
  generated assets/content, dependency locks, fixtures and capture configuration)
  and reconcile them to the resulting code commit before final acceptance.
  Evidence-only/non-rendered docs-only later edits may reuse captures after a
  verified unchanged runtime-input diff; otherwise recapture affected cases.
- Use synthetic data by default. Private inputs and any sharing require existing
  appropriate authorization. Never expose secrets, private machine paths,
  customer/project identifiers or confidential data in images, metadata, URLs,
  traces or logs. Declare masks; do not hide changed content. Keep privacy-safe
  unannotated captures available, not unsafe originals.
- Commit only a small stable baseline set plus the checklist in existing evidence
  paths, or `docs/evidence/frontend/<change>/`. Revalidate reused baselines;
  inspect intended diffs and rerun without snapshot-update flags where supported.
  Put the full collection in exact SHA-bound CI artifacts/PR attachments with an
  image manifest, authorized access and availability through review.
- Run applicable automated checks and exercise changed interactions in the real
  UI; record commands/outcomes and blockers. Screenshots prove appearance only.
  Existing project/native-tool checks still apply. Missing/stale/inaccessible
  evidence, unexplained gaps or unverified interactions block positive Astra/UI
  review acceptance. An unavailable environment is blocked, not passed or N/A.
  This is a documented review gate, not new automatic CI/branch enforcement.

When introducing the first UI, document its actual run/test/capture entry points
alongside this rule so evidence can be reproduced.
