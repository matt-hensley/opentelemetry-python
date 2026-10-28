# Span creation component map

This flow covers `Tracer.start_span` and `Tracer.start_as_current_span`, including API context lookup, sampling, SDK `Span` construction, default attributes, lazy event/link state, and scope activation.

## Source

- `opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py`: `Tracer.start_as_current_span` (around line 1166) and `Tracer.start_span` (around line 1196).
- `opentelemetry-api/src/opentelemetry/trace/__init__.py`: `use_span` (around line 579).
- `opentelemetry-api/src/opentelemetry/context/__init__.py`: `set_value`, `attach`, and `detach`.
- [Shared bounded collections](../../shared/bounded-collections/README.md): span attributes and event/link storage.

## Investigations

- [PERF-006: lazy event and link storage](investigations/PERF-006-lazy-events-links/notes.md) — implemented and validated; retained memory evidence available.
- [PERF-010: lazy span attributes](investigations/PERF-010-lazy-span-attributes/notes.md) — deferred over serialization and counter semantics.
- [PERF-016: delegate to the API span-use generator](../../../api/trace/scope-management/investigations/PERF-016-generator-wrapper/notes.md) — API-owned measured prototype; implementation remains open.

Do not infer allocation counts from `tracemalloc` peak bytes. Keep `start_span` separate from scoped lifecycle results, and keep paired CPU and wall-time evidence labeled separately.
