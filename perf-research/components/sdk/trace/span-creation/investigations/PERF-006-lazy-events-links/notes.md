# Lazy event and link storage

ID: PERF-006  
Status: implemented  
Implementation: working tree  
Last reviewed: 2026-10-15

## Hot path and hypothesis

Recording spans commonly start without events or links. Eagerly allocating two bounded lists costs memory retained for the lifetime of every span. `Span.__init__` now leaves `_events` and `_links` as `None` until initial values or later mutations require storage; accessors and readable-span construction expose empty sequences as before. Source: `opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py` near lines 502–553, 830–846, 895–925, and 948–962.

## Baseline and experiment

The candidate was compared against the saved pre-change API attributes and SDK trace/util sources with 2,000 retained spans per case. See [retained-memory results](../../../../../../evidence/session-2026-10-14-15/artifacts/agent/attribute-audit/retained-memory-comparison.json). The comparison reports `tracemalloc` current and peak bytes; it does not measure allocation counts.

## Results

With 4 span attributes, retained current bytes fell from 2,812.052 to 988.058 bytes per span, a reduction of 1,824 bytes per span. With 10 attributes the reduction was also 1,824 bytes per span. The timing comparison also showed improvements for empty-span sampled and dropped cases, though bundled figures belong to their bundle.

## Compatibility and validation

Events/links properties, JSON formatting, dropped counters, mutation after creation, and readable-span snapshots must remain equivalent. The primary lane ran SDK tests and static checks. This note records that validation as handed off; it is not a new test run.

## Decision and next work

Retain lazy storage. Reopen if a consumer depends on private `_events`/`_links` being eagerly allocated, or if any supported serialization/export path distinguishes the absent internal storage from an empty sequence. Keep retained-memory bytes separate from transient allocation counts.
