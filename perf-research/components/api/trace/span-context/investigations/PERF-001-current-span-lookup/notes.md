# PERF-001: Current-span lookup fast path

ID: PERF-001  
Status: implemented  
Implementation: working tree  
Last reviewed: 2026-10-15

## Hot path and hypothesis

`get_current_span` runs during span creation and instrumentation context checks.
The baseline delegated optional-context lookup to `get_value` and performed an
abstract `isinstance` check even for the exact API `NonRecordingSpan`. The
working-tree change directly fetches current context only when needed and
returns exact `NonRecordingSpan` instances without that ABC check. Source:
[`get_current_span`](../../../../../../../opentelemetry-api/src/opentelemetry/trace/propagation/__init__.py).

## Baseline and experiment

The implementation was validated in a bundled CPU comparison with the SDK
Decision check candidate PERF-002. Raw evidence:
[paired-cpu.json](../../../../../../evidence/session-2026-10-14-15/artifacts/agent/paired-cpu.json).
Do not attribute the bundle’s full change to PERF-001.

## Results

The paired root CPU matrix showed 7.1% and 13.3% lower CPU in the two dropped
local-child `current-span` cases, but also contains PERF-002. These are bundle
results, not isolated PERF-001 effects. The matrix includes root, child,
sampled, and custom-drop controls; the retained gain is largest in dropped-span
creation, the target flow.

## Compatibility and validation

Tests cover exact `NonRecordingSpan`, an API `Span` subclass, a custom Span
implementation, invalid context values, explicit empty context behavior, and
the installed runtime context path. The API test log is archived by the root
evidence collection. Exact type checking is limited to the known concrete
`NonRecordingSpan`; subclass and custom implementation validation remains.

## Decision and next work

Retain the small lookup fast path. Re-run isolated attribution only if a future
change touches this path or profiling shows the remaining lookup dominates.
