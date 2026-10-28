# API attributes component

`BoundedAttributes` cleans values, normalizes keys, enforces limits, tracks
drops, and preserves insertion/update ordering. These operations run during
span construction and mutation, and on event/link creation. Source entry point:
[`opentelemetry.attributes`](../../../../opentelemetry-api/src/opentelemetry/attributes/__init__.py).

| ID | Candidate | Status | Decision |
|---|---|---|---|
| [PERF-004](investigations/PERF-004-cleaned-dict-adoption/notes.md) | Adopt cleaned dict on empty exact base instance | Implemented, working tree | Retained after paired confirmation; guarded to preserve subclass hooks and overflow semantics. |
| [PERF-005](investigations/PERF-005-scalar-type-tuple/notes.md) | Reuse the scalar-type tuple | Implemented, working tree | Retained; avoids rebuilding an `isinstance` tuple during recursive cleaning. |
| [PERF-007](investigations/PERF-007-nonempty-bulk-update/notes.md) | Bulk-update nonempty bounded attributes | Rejected | Gains were workload-dependent and disappeared or reversed on overlap; retained path iterates through ordering/limit logic. |
| [PERF-008](investigations/PERF-008-constructor-specialization/notes.md) | Specialize constructor cleaning | Rejected | Weak 0–3.45% timing changes were inconsistent and too small to justify duplicated constructor logic. |

Related SDK candidates cover the lock on each attribute operation (PERF-009),
lazy per-span storage (PERF-010), and frozen readable snapshots (PERF-011).
Those IDs are maintained by the SDK component owner.

## Unexplored

- Nested list/tuple cleaning and truncation costs have not been isolated by value
  shape or depth.
- Nonempty bulk update alternatives would need evidence across overlap, order,
  bounded overflow, and custom subclass hooks before reopening PERF-007.
