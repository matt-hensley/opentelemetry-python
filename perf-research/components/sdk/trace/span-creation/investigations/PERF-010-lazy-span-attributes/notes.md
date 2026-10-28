# Lazy span attribute storage

ID: PERF-010  
Status: deferred  
Implementation: none  
Last reviewed: 2026-10-15

## Hot path and hypothesis

Every recording `Span` constructs a `BoundedAttributes` container even when its initial attributes are absent. Deferring the container until the first attribute mutation might reduce empty-span setup cost. The owning code is `opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py` around `Span.__init__`, `set_attribute`, `set_attributes`, readable-span creation, and end-time freezing.

## Baseline and experiment

No production prototype or benchmark is retained for lazy span attributes. The idea was reviewed alongside lazy event/link storage; the latter has separate evidence under PERF-006.

## Results

There is no timing or memory result for this candidate.

## Compatibility and validation

The current empty attribute representation serializes as `{}` through `ReadableSpan.to_json`; a missing container may instead serialize as `null` unless normalized. The container also carries dropped-attribute counters, mutability and locking behavior, and is exposed through `ReadableSpan.attributes`. A lazy representation must preserve all of these, including after `Span.end` and when `set_attributes` overflows limits.

## Decision and next work

Defer. Reopen only with a representation that preserves empty JSON shape, read-only views, concurrency semantics, dropped counts, attribute limits, and mutation/freeze behavior, then measure the complete recording-span lifecycle and retained memory.
