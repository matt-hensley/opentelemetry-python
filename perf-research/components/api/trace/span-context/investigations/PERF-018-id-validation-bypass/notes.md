# PERF-018: Bypass SpanContext ID validation

ID: PERF-018  
Status: rejected  
Implementation: none  
Last reviewed: 2026-10-15

## Hot path and hypothesis

Every SDK span constructs a `SpanContext`, whose initializer checks that trace
and span IDs are within range. Since the SDK normally uses an ID generator, a
private trusted constructor might skip these comparisons. Source:
[`SpanContext.__new__`](../../../../../../../opentelemetry-api/src/opentelemetry/trace/span.py)
and [`Tracer.start_span`](../../../../../../../opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py).

## Baseline and experiment

Read-only compatibility review; no candidate was implemented or benchmarked.
The current constructor behavior is the baseline.

## Results

No timing result. The ID generator interface allows custom implementations, and
the SDK currently represents out-of-range generated IDs as invalid
SpanContexts. Skipping validation would change that behavior and could make
invalid IDs look valid to samplers and callers.

## Compatibility and validation

Validation is part of the public `SpanContext` construction contract. A private
trusted path would need to validate or constrain every custom generator and
would add a second construction API. No such compatibility basis was found.

## Decision and next work

Reject. Do not bypass validation. Reopen only if the API gains a compatible,
explicit trust contract for ID generators and end-to-end profiling shows the
range comparisons are material.
