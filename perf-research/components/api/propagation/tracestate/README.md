# Tracestate

[`TraceState.from_header`](../../../../../opentelemetry-api/src/opentelemetry/trace/span.py#L381) splits comma-separated members, trims only SP/HTAB, full-matches each member, rejects duplicate keys, and constructs a `TraceState`. `traceparent` extraction checks the combined tracestate length before calling it ([propagator source](../../../../../opentelemetry-api/src/opentelemetry/trace/propagation/tracecontext.py#L63)).

[`PERF-013`](investigations/PERF-013-tracestate-dict-adoption/notes.md) investigates adopting the already parsed local dictionary for the exact built-in `TraceState`, avoiding another list, validation pass, and dictionary insertion pass. Subclasses and over-limit data retain the existing constructor path in the prototype. The recorded benefit is bundled with traceparent and default-getter work; an isolated tracestate gain has not been measured.
