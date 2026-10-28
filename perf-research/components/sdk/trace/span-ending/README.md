# Span ending component map

`Span.end` validates lifecycle state, records the end time, runs configured end-time callbacks while the span is mutable, freezes attributes, creates a `ReadableSpan`, then dispatches `on_end`. It is a normal-path cost for every recording span, including cases with no exception and no events.

## Source

- `opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py`: `Span.end` near line 978, `_readable_span` near 948, `ReadableSpan.attributes` and event/link views near 496–510.
- `opentelemetry-api/src/opentelemetry/attributes/__init__.py`: bounded attribute access and locking.

## Investigations

- [PERF-011: frozen attribute views](investigations/PERF-011-frozen-attribute-views/notes.md) — deferred; no profile or benchmark yet.
- [PERF-006: lazy event and link storage](../span-creation/investigations/PERF-006-lazy-events-links/notes.md) — owned by span creation; linked here because ending materializes the readable snapshot.

Do not weaken end idempotence, mutation-during-ending callbacks, immutability after callbacks, or snapshot semantics when evaluating this path.
