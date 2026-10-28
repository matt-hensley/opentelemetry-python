# Scope management component

`use_span` attaches a new immutable context, yields to user code, detaches in a
`finally` path, and optionally records exceptions and ends the span. SDK
`start_as_current_span` delegates into this API helper. Sources:
[`trace.use_span`](../../../../../opentelemetry-api/src/opentelemetry/trace/__init__.py)
and [`Tracer.start_as_current_span`](../../../../../opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py).

| ID | Candidate | Status | Decision |
|---|---|---|---|
| [PERF-016](investigations/PERF-016-generator-wrapper/notes.md) | Share the `use_span` generator body with SDK to avoid a nested context-manager wrapper | Measured prototype | Delegate-generator prototype improved common flows; API/SDK integration remains unimplemented pending decorator, async, and exception review. |

## Unexplored

- Native integration across sync/async agnostic context managers has not been
  implemented or validated.
- The inline upper-bound prototype duplicated exception and cleanup logic and
  is not an acceptable implementation direction.
