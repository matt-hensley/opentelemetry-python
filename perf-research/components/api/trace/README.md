# API trace component

This map covers API trace primitives and scope activation. The SDK calls these
interfaces for every span; instrumentation also uses them for context lookup,
scope entry, and propagation. Core source files are
[`span.py`](../../../../opentelemetry-api/src/opentelemetry/trace/span.py),
[`trace/__init__.py`](../../../../opentelemetry-api/src/opentelemetry/trace/__init__.py),
and [`trace/propagation/__init__.py`](../../../../opentelemetry-api/src/opentelemetry/trace/propagation/__init__.py).

| Subcomponent | Hot path | Investigations |
|---|---|---|
| [SpanContext](span-context/README.md) | Read current span and access immutable context fields | [PERF-001](span-context/investigations/PERF-001-current-span-lookup/notes.md), [PERF-018](span-context/investigations/PERF-018-id-validation-bypass/notes.md), [PERF-019](span-context/investigations/PERF-019-native-field-getters/notes.md) |
| [Scope management](scope-management/README.md) | Activate a span and preserve exception/end behavior | [PERF-016](scope-management/investigations/PERF-016-generator-wrapper/notes.md) |

API propagation-specific candidates are documented by the propagation owner.
SDK sampling-decision and TraceFlags work is cross-referenced in the [API map](../README.md)
and global ledger, not duplicated here.

## Unexplored

- SpanContext property getter alternatives (PERF-019) are deferred pending a
  compatibility-preserving benchmark; no native descriptor change is retained.
- SpanContext formatting, equality, and hashing have not been separately
  profiled against ordinary context lookup and sampler access.
- Async scope behavior must be included in any future `use_span` implementation
  change.
