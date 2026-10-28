# SpanContext and current-span component

The API stores a span in `Context` and exposes `get_current_span`; `SpanContext`
is an immutable tuple-like value read by samplers, SDK spans, and propagators.
Sources: [`trace/propagation/__init__.py`](../../../../../opentelemetry-api/src/opentelemetry/trace/propagation/__init__.py)
and [`trace/span.py`](../../../../../opentelemetry-api/src/opentelemetry/trace/span.py).

| ID | Candidate | Status | Decision |
|---|---|---|---|
| [PERF-001](investigations/PERF-001-current-span-lookup/notes.md) | Inline current-context lookup and bypass ABC check for exact `NonRecordingSpan` | Implemented, working tree | Retained; paired SDK comparison includes PERF-002 and is not an isolated attribution. |
| [PERF-018](investigations/PERF-018-id-validation-bypass/notes.md) | Skip `SpanContext` ID range validation for SDK-generated IDs | Rejected | Custom ID generators can return out-of-range IDs, which currently yield invalid contexts. |
| [PERF-019](investigations/PERF-019-native-field-getters/notes.md) | Replace Python tuple-index property getters with native descriptors | Deferred | Potentially hot, but subclass `__getitem__` semantics and typing/specialization need a measured compatible design. |

## Unexplored

- No separate benchmark isolates property access from surrounding sampler and
  span work. Revisit PERF-019 only with compatibility tests for subclasses and
  repeated-access end-to-end evidence.
- Trace-context parsing/formatting belongs to the separate API propagation map.
