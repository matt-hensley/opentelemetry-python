# Session evidence: October 14–15, 2026

The [manifest](manifest.json) inventories 70 original artifacts with SHA-256
hashes, original paths, and timestamps. These files were copied byte for byte
from the session's ignored `.agent` directory. Preserve them unchanged, including
failed and superseded attempts. The [ledger](../../ledger.json) connects preferred
studies to owning investigations.

## Preferred evidence

Paths in this table are relative to [artifacts/agent](artifacts/agent/).

| Study | Result files | Interpretation |
|---|---|---|
| S01 | [paired-cpu.json](artifacts/agent/paired-cpu.json) | Lookup and Decision bundle against saved Git function baselines |
| S02 | [context-copy-probe.json](artifacts/agent/context-copy-probe.json) | Rejected one-copy context insertion |
| S03 | [final confirmation](artifacts/agent/attribute-audit/paired-final-confirmation.json), [earlier component comparison](artifacts/agent/attribute-audit/paired-attribute-confirmation.json), [memory cohorts](artifacts/agent/attribute-audit/retained-memory-comparison.json) | Attribute/storage bundle; final confirmation includes scalar tuple reuse; memory is retained traced bytes |
| S04 | [cleaner comparison](artifacts/agent/attribute-audit/paired-cleaner-comparison.json) | Isolated scalar tuple reuse |
| S05 | [bulk comparison](artifacts/agent/attribute-audit/paired-bulk-comparison.json) | Rejected nonempty update tradeoffs |
| S07 | [extract comparison](artifacts/agent/propagation-audit/paired-extract-comparison.json) | Three propagation prototypes together; no individual attribution |
| S08 | [parser alternatives](artifacts/agent/propagation-audit/paired-parser-comparison.json), [strip follow-up](artifacts/agent/propagation-audit/paired-strip-comparison.json) | Rejected replacements for optimized regex; 11,770-header differential preflight |
| S09 | [contextmanager comparison](artifacts/agent/lifecycle-audit/paired-contextmanager-comparison.json) | Shared generator prototype and duplicated inline upper bound |
| S10 | [parent reuse](artifacts/agent/lifecycle-audit/paired-parent-reuse-comparison.json) | Built-in sampler parent reuse; unresolved extension hooks |
| S11 | [combined comparison](artifacts/agent/lifecycle-audit/paired-combined-comparison.json), [counted confirmation](artifacts/agent/lifecycle-audit/paired-combined-counted-comparison.json) | Unsampled rows from the first file; sampled pipeline claim only from the counted second file |

Original Python harnesses sit beside the results. Their original output paths
point into `.agent`; use the [replay tool](../../tools/replay.py) and
[execution instructions](../../README.md#running-benchmarks) for fresh runs.
Replay stages scripts into an isolated output directory and measures the current
checkout. It does not reconstruct every historical module or environment.

## Weak, excluded, and historical material

- **S06 constructor specialization:** [constructor comparison](artifacts/agent/attribute-audit/paired-ctor-comparison.json)
  uses short, quantized CPU batches. Its harness was persisted after measurement.
  The small apparent gains do not establish a useful improvement.
- **Uncounted sampled batch row:** the sampled row in the original combined
  comparison is excluded. A subsequent count check with the default queue
  exported 8,452 of 10,000 spans. That check establishes the need for counting;
  it does not identify the exact loss in the original run. The counted rerun
  uses a queue of 131,072, asserts every exported count, and includes draining.
- Early pytest-benchmark JSON and logs include exploratory runs and failed
  attempts. `candidate-cpu-repeat-1.json` is intentionally empty. Do not select
  the fastest historical run to replace the paired comparisons above.
- Logs have their original scope and dates. The final retained-tree suite counts
  are recorded in [validation-observed.json](validation-observed.json) from
  observed conversation output; older logs are not represented as those runs.

## Source identity and environment

The session HEAD is `155ead5140311a98b59c876819b96007001c3fed`.
The working tree was dirty. See the root [baseline table](../../README.md#evidence-and-baseline-stages)
and manifest for B0, B1, and B2; they are different experiment baselines.

- [working-tree/](working-tree/) contains ten retained source/test/benchmark
  snapshots, with `.snapshot` suffixes to avoid test collection. The manifest maps
  each snapshot to its original path and hash. These are the retained B2 files,
  without the runtime propagation/lifecycle prototypes.
- [production-working-tree.patch](production-working-tree.patch) records tracked
  production differences. Untracked benchmark/changelog files are in the source
  snapshots; they are absent from this patch.
- [environment.txt](environment.txt) records Python and platform.
  [environment-freeze.txt](environment-freeze.txt) records the installed package
  list captured while documenting this session. It is not a historical lockfile.
- Original measurements used CPython 3.13.14 on Windows. Individual artifacts
  record their own affinity, source/harness hashes, loops, warmups, and samples.

Restore snapshots only in an isolated checkout after reviewing the patch and
manifest. The archive does not contain a complete historical installed environment
or every unmodified repository file.

## Profiles

The original [sdk_profile.py](artifacts/agent/sdk_profile.py),
[dropped-span profile](artifacts/agent/dropped-span-profile.pstats), and
[sampled-span profile](artifacts/agent/sampled-span-profile.pstats) map work before
the retained attribute/storage changes. They profile nested current-span scopes
without an exporter. Use them for call paths and counts; profiler times do not
establish candidate savings. See [current profiling commands](../../README.md#running-profiles)
to produce a fresh profile with environment and source metadata.
