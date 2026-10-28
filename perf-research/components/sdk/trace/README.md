# Trace SDK map

This subtree follows the SDK trace path from parent resolution through sampling, recording-span construction, ending, and processor callbacks.

## Component maps

- [Sampling](sampling/README.md)
- [Span creation](span-creation/README.md)
- [Span ending](span-ending/README.md)
- [Processor dispatch](processors/README.md)

The common container cost belongs to [shared bounded collections](../shared/bounded-collections/README.md). Do not repeat those details in per-flow notes.

## Flow summary

`Tracer.start_span` resolves the parent from the supplied or active API context, asks the configured sampler, builds a `SpanContext`, and returns a `NonRecordingSpan` for a drop decision. Recording decisions construct and start the SDK `Span`. `start_as_current_span` adds activation and scope cleanup around `start_span`. On ending, a recording span runs synchronous ending callbacks, freezes its attributes, constructs a `ReadableSpan`, and dispatches end callbacks.

Source entry points are `opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py` (`Tracer.start_span` near line 1196, `Tracer.start_as_current_span` near 1166, `Span.start` near 965, and `Span.end` near 978) and `opentelemetry-sdk/src/opentelemetry/sdk/trace/sampling.py`.
