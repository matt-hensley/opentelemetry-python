# API context component

`Context` is an immutable mapping carried by the selected runtime context. The
common tracing path reads the current context to find a span, then activation
copies a context and attaches the new value. Source entry points are
[`context.get_current` and `set_value`](../../../../opentelemetry-api/src/opentelemetry/context/__init__.py)
and [`Context`](../../../../opentelemetry-api/src/opentelemetry/context/context.py).

| ID | Candidate | Status | Decision |
|---|---|---|---|
| [PERF-003](investigations/PERF-003-context-copy/notes.md) | Avoid a temporary dict copy in `set_value` | Rejected | Exact-Context path used 10–38% more median CPU and 13–31% more median wall time; retain current behavior. |

## Unexplored

- Runtime context provider internals, beyond the current-span lookup documented
  in [PERF-001](../trace/span-context/investigations/PERF-001-current-span-lookup/notes.md),
  have not been independently optimized.
- Broader context representation changes are out of scope without a measured
  workload and compatibility plan for third-party `Context` subclasses.
