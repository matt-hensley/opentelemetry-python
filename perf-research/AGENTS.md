# Performance research maintenance

This directory records the tracing performance investigation. Follow the repository
AGENTS.md and contribution rules as well as this file. The root README contains
benchmark and profiling commands; keep execution instructions there.

## Before working

1. Read README.md, ledger.json, the relevant component README, and the relevant
   flow map. Read existing investigation notes before repeating an experiment.
2. Check the implementation and evidence status. A measured prototype is not an
   implemented optimization; an implemented working-tree change is not merged.
3. Coordinate ownership. The sibling perf-audit worktree owns shared empty
   SamplingResult attributes and TraceFlags allocation work. Do not duplicate it
   without checking the current handoff.

## Keep the tree current

- Give each candidate one stable PERF-NNN ID and one owning component. Other
  components and flow maps link to that investigation rather than copying it.
- Update ledger.json, investigation notes, the component README, and affected
  flow maps together when the finding or status changes.
- Use the root template for new investigations. Record the hypothesis, ordinary
  hot-path frequency, source entry points, baseline, experiment, compatibility
  requirements, evidence, decision, and conditions for revisiting it.
- Record rejected and deferred ideas, including why they were rejected and what
  would justify reopening them. Mark unexplored areas explicitly.
- Keep factual observations separate from hypotheses and projections. Link
  source paths and evidence. Avoid restating whole modules in prose.

## Evidence rules

- Preserve archived artifacts unchanged. New runs go in .runs/ or a new evidence
  directory, with a manifest, source hashes, environment, and exact command.
- A Git commit alone does not identify a dirty worktree. Record the relevant
  source hashes and patch or source snapshot. Never silently change a baseline.
- Measure one CPU-heavy experiment at a time. Keep setup, warmup, and functional
  checks outside timed batches. Preserve raw paired samples and CPU and wall
  summaries. See README.md for the measurement protocol.
- Distinguish individual, bundled, incremental, and cumulative comparisons. Do
  not add percentages from different baselines or attribute a bundle's gain to
  one member without an isolated comparison.
- Verify generated and exported counts in processor benchmarks and include queue
  draining in timing. Preserve invalid runs with an explicit exclusion reason.
- A profile locates work; its instrumented timings are not benchmark results.
- Do not promote weak or invalid measurements into headline claims. The archived
  constructor specialization results are weak, and the uncounted batch result
  was excluded after a later default-queue run dropped spans.

## Implementation and review

- Keep production changes and upstream PRs scoped separately from this research
  corpus. This directory is a research record, not a request to bundle all work
  into one PR. Do not post AI-written issue or PR comments.
- Preserve custom samplers, getters, runtime contexts, subclass behavior, lazy
  creation, decorators, exception behavior, limits, and dropped counters where
  applicable. Record unresolved compatibility questions before proposing a patch.
- Record validation commands and outcomes, including platform skips and existing
  warnings. Follow the user's authorization for running tests and benchmarks.
- After documentation changes, check JSON syntax, local links, candidate IDs,
  evidence references, and agreement between notes and the ledger. Production
  implementation validation remains a separate activity.
  Run `.venv/Scripts/python.exe perf-research/tools/check.py` from the repository
  root. Resolve documentation errors; current-source drift is informational.

## Delegation

Assign one component or investigation to an agent. Give it the owning ID, files
it may edit, baseline, and whether it owns the timing lane. Agents must report
artifacts and unresolved questions. Only one agent runs performance measurements
at a time. Read the root index and the relevant subtree rather than loading the
entire evidence archive into context.
