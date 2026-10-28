# Skip empty span-processor dispatch

ID: PERF-020  
Status: deferred  
Implementation: none  
Last reviewed: 2026-10-15

## Hot path and hypothesis

With no registered processors, `Span.start` and `Span.end` still call the multi-processor's `on_start`, `_on_ending`, and `on_end`, each of which iterates an empty tuple. `Span.end` also builds a `ReadableSpan` before the no-op end dispatch. Source: `opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py` around lines 154–216 and 965–1000.

## Baseline and experiment

Profiles show these functions on sampled paths, but no isolated comparison quantifies dispatch or `ReadableSpan` creation. Existing end-to-end benchmarks use providers without processors in some cases; these are not sufficient to isolate a safe fast path for configured processors.

## Results

No dedicated performance result. Treat the profile as location evidence only.

## Compatibility and validation

`TracerProvider.add_span_processor` can register a processor after tracer/span creation. A fast path based on an empty processor collection could skip callbacks if registration races with span start/end, and omitting `ReadableSpan` can change what a late-added processor receives. Configured SDKs commonly have processors, so this candidate does not apply to those callback paths. Processor order, callback timing, exception handling, and queue draining must remain intact.

## Decision and next work

Defer. Reopen with a documented registration/snapshot contract, an implementation that preserves callback semantics, and a counted benchmark including queue drain for at least empty and one-processor controls. Do not use the earlier uncounted sampled batch result: a subsequent default-queue count check lost 1,548 of 10,000 spans, so uncounted comparisons are unreliable. The exact loss in the original run is unknown.
