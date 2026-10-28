# PERF-003: Context update copy

ID: PERF-003  
Status: rejected  
Implementation: none  
Last reviewed: 2026-10-15

## Hot path and hypothesis

`context.set_value` is used for span activation. It calls `Context.copy()`, writes
to that temporary dict, then constructs a second `Context` from it. The proposal
was to construct `Context(context)` and write through `dict.__setitem__` to avoid
the temporary dict. Sources: [`set_value`](../../../../../../opentelemetry-api/src/opentelemetry/context/__init__.py)
and [`Context`](../../../../../../opentelemetry-api/src/opentelemetry/context/context.py).

## Baseline and experiment

The baseline was the repository implementation at the API/SDK benchmark
snapshot. A direct exact-Context candidate was compared with baseline in
`.agent/context_copy_probe.py`; artifact:
[context-copy-probe.json](../../../../../evidence/session-2026-10-14-15/artifacts/agent/context-copy-probe.json).
The harness uses five alternating rounds of one million operations for context
sizes 0, 1, 2, and 8 with GC disabled. This early probe did not record source
hashes or environment metadata in its result; do not infer those fields from
later, better-instrumented studies.

## Results

The candidate used about 10–38% more median CPU and 13–31% more median wall time
across the measured context-size cases. These early CPU batches were short
(roughly 0.2–0.4 seconds) and quantized; treat the exact percentages cautiously.
The
avoided dict allocation did not offset the extra direct `dict.__setitem__` call
on these small contexts. This rules out retaining that implementation on the
tested interpreter/workloads; a different representation or runtime-specific
implementation would need a new measurement.

## Compatibility and validation

The proposed path also bypassed custom `Context.copy()` behavior. An exact-type
fast path with the old subclass fallback could preserve that hook, but it does
not address the measured slowdown. No source change is retained.

## Decision and next work

Reject. Keep the existing copy path. Reopen only with a materially different
candidate that preserves subclass behavior and improves the measured tiny
contexts, including 0–2 entry maps.
