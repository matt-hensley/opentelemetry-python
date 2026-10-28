# Shared bounded collections

The SDK span path uses two bounded storage families:

- API `BoundedAttributes` cleans, bounds, and optionally freezes attribute mappings used by spans, events, links, and other API/SDK objects.
- SDK `BoundedList` limits event and link retention and tracks dropped items.

## Source

- `opentelemetry-api/src/opentelemetry/attributes/__init__.py`: `_clean_attribute_value`, `BoundedAttributes._set_items`, and bounded insertion.
- `opentelemetry-sdk/src/opentelemetry/sdk/util/__init__.py`: `BoundedList` and its append/from-sequence paths.
- SDK callers: `opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py` in span construction and mutation.

## Investigations

- [PERF-009: shared attribute lock](investigations/PERF-009-shared-attribute-lock/notes.md) — deferred; no timing, with reentrancy and aliasing risks.
- [PERF-006: lazy event and link storage](../../trace/span-creation/investigations/PERF-006-lazy-events-links/notes.md) — allocated list avoidance is owned by span creation.

Keep API cleanup, ordering, drop counts, lock semantics, and bounded-list ring behavior distinct from SDK lifecycle overhead. `tracemalloc` retained/peak bytes are memory evidence, not allocation counts.
