# OpenTelemetry Python performance research

This is the tracing API and SDK performance investigation from October 14 and 15,
2026. Start with the [candidate ledger](ledger.json), then the relevant component
and flow. [AGENTS.md](AGENTS.md) defines maintenance rules. This README owns the
benchmark and profiling instructions.

The target is substantial CPU reduction on ordinary hot flows, using Python and
the existing public architecture. Instrumentation, exporter serialization, and
transport are later work. Results here measure SDK/API operations; application
savings require a representative application measurement.

## Current state

The ledger contains 20 considered candidates. Five are implemented in the
**uncommitted production working tree**: current-span lookup, sampling-decision
checking, attribute dictionary adoption, scalar-type tuple reuse, and lazy
event/link storage. Propagation and lifecycle proposals remain **runtime
prototypes**. No result in this corpus establishes a cumulative application CPU
reduction or a merged optimization.

| Evidence | Observed result | Scope |
|---|---|---|
| [Lookup and decision bundle](components/api/trace/span-context/investigations/PERF-001-current-span-lookup/notes.md) | Dropped-child start/end about 20–22% less CPU; child scopes about 7–13% | Two changes measured together against original function baselines |
| [Attributes and storage](components/api/attributes/investigations/PERF-004-cleaned-dict-adoption/notes.md) | Sampled start/end with 4/10 attributes: 20.4/21.1% less CPU; current scope with 10: 12.6% | Incremental over earlier lookup/decision work; includes scalar tuple and lazy lists |
| [Lazy containers](components/sdk/trace/span-creation/investigations/PERF-006-lazy-events-links/notes.md) | About 1,824 fewer retained traced bytes per live sampled span | Cohorts without events or links; retained tracemalloc memory, not RSS |
| [Propagation bundle](components/api/propagation/traceparent/investigations/PERF-012-regex-wrapper/notes.md) | Full extraction about 29–44% less CPU with default getter; 29–39% with custom getter | Three changes bundled; not individually attributed |
| [Scope and parent reuse](components/api/trace/scope-management/investigations/PERF-016-generator-wrapper/notes.md) | Combined unsampled root/child scopes: 25.5/23.2% less CPU | Incremental prototypes over retained worktree |
| [Counted batch pipeline](components/sdk/trace/sampling/investigations/PERF-017-parent-context-reuse/notes.md) | Combined sampled child with 4 attributes: 8.7% less CPU, 9.8% less wall time | BatchSpanProcessor, no-I/O exporter, large queue, every span counted, drain timed |

These percentages describe different comparisons. They cannot be added. See each
study's baseline and participants in the ledger. The original uncounted batch
result was excluded; a subsequent default-queue count check exported only 8,452
of 10,000 requested spans. Only the counted rerun supports the sampled pipeline
claim above.

## Navigate by component

~~~text
perf-research/
  README.md                   Commands, protocol, and research overview
  AGENTS.md                   Maintenance and evidence rules
  ledger.json                 Candidate IDs, status, ownership, and studies
  components/{api,sdk}/        Component maps and nested investigation notes
  flows/                      Incoming, unsampled, and sampled paths
  evidence/<session>/         Immutable results, harnesses, and source snapshots
  templates/                  New investigation template
  tools/                      Replay, profiling, and documentation checks
  .runs/                      Ignored fresh outputs
~~~

- [API](components/api/README.md)
  - [Context](components/api/context/README.md)
  - [Attributes](components/api/attributes/README.md)
  - [Propagation](components/api/propagation/README.md): traceparent, tracestate,
    text-map getters, and unexplored baggage
  - [Tracing](components/api/trace/README.md): span context and scope management
- [SDK](components/sdk/README.md)
  - [Tracing](components/sdk/trace/README.md): sampling, span creation, ending,
    and processor handoff
  - [Shared collections](components/sdk/shared/bounded-collections/README.md)

A component README records responsibilities, source entry points, inspected
areas, unknowns, and links to investigations. Each candidate has one owning
component and one stable PERF-NNN ID.

## Navigate by ordinary flow

- [Incoming request](flows/incoming-request.md)
- [Unsampled span](flows/unsampled-span.md)
- [Sampled span](flows/sampled-span.md)

These maps cross component boundaries. They identify where candidates compose
and where a profile or experiment has not yet been performed.

## Evidence and baseline stages

The [session evidence index](evidence/session-2026-10-14-15/README.md) and
[manifest](evidence/session-2026-10-14-15/manifest.json) preserve 70 original
artifacts, source hashes, the dirty source snapshot, environment, and exclusions.
The archive is immutable. It includes rejected experiments and historical failed
attempts; use the preferred studies in the ledger for claims.

| Stage | Meaning |
|---|---|
| B0 | Lookup and Decision functions loaded from session Git revision 155ead5140311a98b59c876819b96007001c3fed; remaining runtime was that experiment's checkout |
| B1 | Saved attribute/trace/util modules after lookup/decision changes, before attribute and event/link changes |
| B2 | Retained working-tree code captured in the session snapshot; baseline for propagation and lifecycle prototypes |

A Git revision does not identify the dirty source tree. The manifest records the
relevant source hashes and snapshots. Snapshot filenames end in .snapshot so
archived tests are not collected. The snapshot includes untracked production
benchmark files; the Git patch alone does not contain them.

## Running benchmarks

Run from the repository root using its editable packages and virtual environment.
The recorded environment is CPython 3.13.14 on Windows; many experiments pin the
process to CPU 0. Windows process CPU accounting is quantized at about 15.625 ms,
so short batches are weak evidence.

The replay tool verifies archived hashes and stages source files into a fresh,
ignored perf-research/.runs directory. It rewrites original .agent output paths,
keeps the source archive unchanged, and pins the lookup experiment's Git function
baseline to the session revision. It records the current source hashes and
command in run.json. **Replay is a new measurement against current editable
sources**, not an automatic reconstruction of the entire historical tree.

~~~powershell
.venv/Scripts/python.exe perf-research/tools/replay.py list
.venv/Scripts/python.exe perf-research/tools/replay.py run --prepare-only propagation
.venv/Scripts/python.exe perf-research/tools/replay.py run propagation
.venv/Scripts/python.exe perf-research/tools/replay.py run attributes -- --preflight-only
.venv/Scripts/python.exe perf-research/tools/replay.py run attributes -- --target-seconds 0.8 --repeats 9 --case-filter "attributes/start-span/constructor/4/"
.venv/Scripts/python.exe perf-research/tools/replay.py run scope
.venv/Scripts/python.exe perf-research/tools/replay.py run parent-reuse
.venv/Scripts/python.exe perf-research/tools/replay.py run combined-counted -- --seconds 1 --repeats 11
~~~

Inspect each archived harness and its notes before replaying it. Some scripts use
source-string replacements that intentionally fail if code has changed. The
scalar-tuple script requires the pre-hoisting source; running it against the
retained hoisted source is not a supported comparison. Constructor replay retains
its original short, quantized batches and is not evidence for a strong win. The
uncounted combined experiment's sampled row is excluded; use combined-counted.

For the package benchmark harness, choose the same benchmark parameters and
dependencies on both revisions:

~~~powershell
.venv/Scripts/python.exe -m pytest opentelemetry-sdk/benchmarks/trace/test_benchmark_dropped_spans.py --benchmark-only --benchmark-json=perf-research/.runs/dropped-run.json
.venv/Scripts/python.exe -m pytest opentelemetry-sdk/benchmarks/trace/test_benchmark_span_attributes.py --benchmark-only --benchmark-json=perf-research/.runs/attributes-run.json
~~~

Create the output directory first and use a new filename per run. The 75-case
smoke check used --benchmark-disable; it validates execution, not performance.

### Measurement protocol

1. Confirm environment, source hashes, baseline stage, controls, and eligibility
   for the ordinary flow. Keep setup outside timing.
2. Give one process the timing lane. Avoid simultaneous tests, profiles, or other
   CPU-heavy experiments. Warm implementations before recording batches.
3. Use fixed operations per paired batch, alternating or balanced mode order.
   Target at least roughly 0.6–1 second per batch and multiple pairs; preserve raw
   samples. Record CPU and wall time separately.
4. Apply GC handling and CPU affinity consistently. Report the actual protocol,
   including departures in older experiments, instead of assuming all scripts
   implement the latest protocol.
5. For processors, count requested and exported spans, avoid drops, and include
   queue draining in the measured batch. Record queue capacity and exporter work.
6. Keep individual and combined comparisons separate. Confirm the complete
   candidate stack against a stable original baseline before making cumulative
   claims. That full-stack comparison remains open.
7. Link functional checks and authorized regression validation. Prototype
   preflights do not constitute a full regression suite.

## Running profiles

Use a profile to locate call counts and expensive stages, then measure candidates
without the profiler. Instrumented times distort Python/C comparisons.

~~~powershell
.venv/Scripts/python.exe perf-research/tools/profile_tracing.py --scenario dropped --loops 100000
.venv/Scripts/python.exe perf-research/tools/profile_tracing.py --scenario sampled --loops 100000
~~~

The tool profiles two nested current-span scopes per iteration and writes
profile.pstats, summary.txt, and source/environment metadata under .runs. The
sampled scenario uses four string attributes and no exporter. The archived
profiles predate retained attribute/storage changes and are historical maps.

## Validation observed in the session

The [validation record](evidence/session-2026-10-14-15/validation-observed.json)
distinguishes observed conversation output from archived raw logs. Retained
production changes passed 297 API tests, 917 SDK tests, and 75 benchmark smoke
cases. Platform skips, existing SDK shutdown messages, and static-check setup are
recorded there. These suites were not rerun while writing this corpus.

For an authorized implementation validation, run API and SDK tests in separate
processes. On Windows, SDK subprocess tests need the virtual environment's Python
on PATH:

~~~powershell
$taskVenvBin = Join-Path (Get-Location).Path '.venv\Scripts'
$env:PATH = "$taskVenvBin;$env:PATH"
python -m pytest opentelemetry-api/tests -q
python -m pytest opentelemetry-sdk/tests -q
~~~

Focused Pyright checking used --pythonpath .venv/Scripts/python.exe and
--pythonplatform Linux to model fork-capable CI. The Linux setting avoids
pre-existing Windows stubs for os.register_at_fork; it does not establish runtime
validation on Linux.

## Next work

After editing this corpus, check its links, candidate/study references, JSON,
and archived hashes:

~~~powershell
.venv/Scripts/python.exe perf-research/tools/check.py
~~~

This checks documentation integrity. It reports current-source drift separately
because later implementation work is expected to differ from historical snapshots.

Prioritize production-quality propagation and shared-generator patches, then a
safe internal parent-context handoff. Preserve public/custom hooks and avoid
duplicating semantic implementations. Refresh profiles and establish cumulative
measurements after implementation.

Coordinate with the sibling perf-audit worktree on shared empty SamplingResult
attributes and TraceFlags allocations. Metrics, logs, baggage, outgoing
propagation, instrumentation, and exporter transport need their own evidence
before expansion. Keep upstream implementation PRs focused; this corpus remains
the broader research record.
