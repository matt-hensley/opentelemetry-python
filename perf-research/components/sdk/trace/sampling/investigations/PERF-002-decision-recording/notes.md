# Decision recording identity check

ID: PERF-002  
Status: implemented  
Implementation: working tree  
Last reviewed: 2026-10-15

## Hot path and hypothesis

Every sampler result is checked to decide whether a recording SDK `Span` should be created. `Decision.is_recording` can determine this from the enum singleton identity rather than membership in a tuple. The implementation is in `opentelemetry-sdk/src/opentelemetry/sdk/trace/sampling.py` near line 156.

## Baseline and experiment

The change was validated only as part of the broader candidate bundle. See the archived paired lifecycle bundle in [the 2026-10-14 agent artifacts](../../../../../../evidence/session-2026-10-14-15/artifacts/agent/paired-cpu.json). Related bundle members are recorded under PERF-001 in the root ledger. The bundle does not isolate this method, so its aggregate gain must not be attributed to PERF-002.

## Results

The combined bundle improved the measured dropped and sampled lifecycle cases, but there is no isolated end-to-end PERF-002 estimate. The saved profile is location evidence, not a benchmark. No per-allocation claim is made.

## Compatibility and validation

The method returns true for `RECORD_ONLY` and `RECORD_AND_SAMPLE`, and false for `DROP`. The current implementation uses enum identity. The SDK tests and static checks were run by the primary implementation lane; this note does not claim independent validation.

## Decision and next work

Retain the focused identity check. Revisit only if an isolated representative benchmark shows a regression or if decision values cease to be enum singletons. Keep PERF-001 bundle evidence separate from this candidate's isolated evidence.
