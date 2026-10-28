# Cache a frozen readable-span attribute view

ID: PERF-011  
Status: deferred  
Implementation: none  
Last reviewed: 2026-10-15

## Hot path and hypothesis

`ReadableSpan.attributes` constructs a `MappingProxyType` view whenever the property is read. A view cached after the recording span freezes its attributes might avoid repeated wrapper allocation for processors that read the property more than once. Source: `opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py` around `ReadableSpan.attributes` and `Span.end`.

## Baseline and experiment

No profile isolates repeated `ReadableSpan.attributes` access, and no timing or allocation experiment has been run for this candidate.

## Results

Unexplored. Do not infer that property wrapper creation is hot from the cost of the overall span end path.

## Compatibility and validation

`ReadableSpan` can be constructed independently of a live `Span`; the attributes mapping may be absent or supplied as another mapping. A cache must preserve read-only behavior and snapshot/freeze semantics, including the period when ending callbacks may still mutate the span. Existing object identity of successive mapping views should not be assumed without checking documented contracts and tests.

## Decision and next work

Defer pending a profile that demonstrates repeated view access in an ordinary processor path. Reopen only if that profile and an isolated benchmark show a material cost and the cached view can preserve independent `ReadableSpan` construction and end-callback mutation rules.
