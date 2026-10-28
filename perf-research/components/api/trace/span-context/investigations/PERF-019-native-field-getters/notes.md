# PERF-019: Native SpanContext field getters

ID: PERF-019  
Status: deferred  
Implementation: none  
Last reviewed: 2026-10-15

## Hot path and hypothesis

`SpanContext` exposes six tuple-index fields through Python `@property` methods.
These reads occur in samplers, SDK span accessors, and propagation. A standard
library native tuple-field descriptor or `operator.itemgetter` property might
reduce Python getter overhead. Source:
[`SpanContext`](../../../../../../../opentelemetry-api/src/opentelemetry/trace/span.py).

## Baseline and experiment

Read-only design review; no implementation or benchmark has been run. Proposed
options included reusing descriptors from a private `namedtuple`, or binding
`operator.itemgetter` behind typed properties.

## Results

No timing result. Native named-tuple descriptors may bypass a subclass’s
overridden `__getitem__`, changing existing behavior. `property(itemgetter(...))`
appears to retain indexing semantics, but its typing shape and CPython attribute
specialization effects are unverified. These are compatibility/performance
hypotheses, not measured results.

## Compatibility and validation

Preserve `SpanContext` tuple layout, constructor, repr, pickling, public property
annotations, and subclass `__getitem__` behavior. Any experiment needs both
direct repeated field-access microbenchmarks and normal sampled-span flows.

## Decision and next work

Defer. Do not install native descriptors without a compatibility-preserving
prototype and end-to-end gain large enough to justify implementation complexity.
