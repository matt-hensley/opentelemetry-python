# Span processor component map

`TracerProvider` owns a synchronous or concurrent multi-processor. Recording span start and end dispatch through that object; `_on_ending` remains synchronous so callbacks can mutate a span before it freezes. Exporter implementation and instrumentation work are outside this map.

## Source

- `opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py`: `SynchronousMultiSpanProcessor` near line 154, `ConcurrentMultiSpanProcessor` near 227, `Span.start` near 965, and `Span.end` near 978.
- `TracerProvider.add_span_processor` appends processors to the active processor collection; registration is allowed after provider creation.

## Investigations

- [PERF-020: empty processor dispatch](investigations/PERF-020-empty-dispatch/notes.md) — deferred; no timing evidence and late-registration behavior needs preservation.
- [PERF-006: lazy event and link storage](../span-creation/investigations/PERF-006-lazy-events-links/notes.md) — span data allocation is owned by span creation, not callback dispatch.

Counted processor comparisons must verify emitted span counts and include queue draining. The earlier uncounted batch result is excluded; see PERF-020 and the root evidence ledger.
