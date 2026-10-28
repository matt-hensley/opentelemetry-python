# API component map

This subtree tracks API-side CPU and allocation work on tracing flows. The API is
called by instrumentation and the SDK; candidates here should preserve public
contracts and extension behavior. See the [global ledger](../../ledger.json) and
[measurement protocol](../../README.md) for status and repeatable commands.

| Component | Hot path | Investigations |
|---|---|---|
| [Context](context/README.md) | Current context lookup and immutable context update | [PERF-003](context/investigations/PERF-003-context-copy/notes.md) |
| [Propagation](propagation/README.md) | Extract traceparent and tracestate through carrier getters | PERF-012 through PERF-015 in the propagation map |
| [Attributes](attributes/README.md) | Clean and bound attributes when spans and events are created or updated | [PERF-004](attributes/investigations/PERF-004-cleaned-dict-adoption/notes.md), [PERF-005](attributes/investigations/PERF-005-scalar-type-tuple/notes.md), [PERF-007](attributes/investigations/PERF-007-nonempty-bulk-update/notes.md), [PERF-008](attributes/investigations/PERF-008-constructor-specialization/notes.md) |
| [Trace](trace/README.md) | Read current span, access SpanContext fields, and activate spans | [PERF-001](trace/span-context/investigations/PERF-001-current-span-lookup/notes.md), [PERF-016](trace/scope-management/investigations/PERF-016-generator-wrapper/notes.md), [PERF-018](trace/span-context/investigations/PERF-018-id-validation-bypass/notes.md), [PERF-019](trace/span-context/investigations/PERF-019-native-field-getters/notes.md) |

The corresponding [SDK map](../sdk/README.md) owns sampling, span storage,
and processor handoff. Shared empty `SamplingResult` attributes and fewer
`TraceFlags` allocations belong to the sibling `../perf-audit` worktree and have
no candidate IDs in this ledger. Shared locks, lazy span attributes, and frozen
views are tracked here as PERF-009, PERF-010, and PERF-011 in the SDK subtree.

## Unexplored

- Outgoing propagation, baggage, and composite propagation remain unexplored;
  incoming W3C extraction is covered by the propagation component.
- Context runtime-provider implementations beyond the direct current-span lookup
  in PERF-001 have not had a separate hot-path audit.
- SpanContext equality/hash behavior and API-level formatting are not measured here.
