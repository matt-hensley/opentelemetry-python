# SDK performance component map

The SDK consumes API contexts and spans, applies sampling, and constructs recording spans when sampling permits. This map follows the tracing lifecycle; it does not cover exporters or instrumentation libraries.

## Areas

- [Trace SDK map](trace/README.md): sampling, span creation, span ending, and processor dispatch.
- [Bounded collections](shared/bounded-collections/README.md): SDK event/link lists and the shared API attribute container.

## Hot-path entry points

- `opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py`: `Tracer.start_span`, `Tracer.start_as_current_span`, `Span.start`, `Span.end`, and multi-processor dispatch.
- `opentelemetry-sdk/src/opentelemetry/sdk/trace/sampling.py`: sampling decisions and built-in samplers.
- `opentelemetry-api/src/opentelemetry/attributes/__init__.py`: `BoundedAttributes`, used for span attributes.
- `opentelemetry-sdk/src/opentelemetry/sdk/util/__init__.py`: `BoundedList`, used for events and links.

## Investigations

The status and evidence for each candidate live in its owning area. Prototype results are not production changes. Cumulative results must not be attributed to one candidate unless an isolated comparison supports that attribution.
