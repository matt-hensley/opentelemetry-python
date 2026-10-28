# Sampling component map

Sampling runs on every enabled SDK `start_span`. The tracer resolves the parent, invokes the configured sampler, translates the decision to trace flags, and either returns a non-recording span or builds a recording SDK span.

## Source

- `opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py`: parent lookup and sampler call in `Tracer.start_span` (around lines 1196–1250).
- `opentelemetry-sdk/src/opentelemetry/sdk/trace/sampling.py`: `Decision`, `StaticSampler`, `TraceIdRatioBased`, and `ParentBased` (around lines 148–360).

## Investigations

- [PERF-002: recording decision check](investigations/PERF-002-decision-recording/notes.md) — implemented; validated only within the combined SDK/API bundle.
- [PERF-017: parent context reuse](investigations/PERF-017-parent-context-reuse/notes.md) — measured prototype; unresolved exact-instance sampler hooks prevent promotion.

Keep custom sampler dispatch and trace-state behavior in scope when evaluating this path. The parent-reuse prototype is not production code.
