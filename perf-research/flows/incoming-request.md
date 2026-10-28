# Incoming request tracing

Follow a typical request carrying a valid lowercase W3C traceparent and absent
or short tracestate. This map covers the repository's API/SDK work. Framework
instrumentation is an external boundary.

~~~mermaid
flowchart LR
  A[Carrier and getter] --> B[TraceContext extraction]
  B --> C[SpanContext and NonRecordingSpan]
  C --> D[Context insertion]
  D --> E[Tracer start]
  E --> F[ParentBased sampling]
  F --> G[Recorded or dropped span]
~~~

| Stage | Evidence and coverage |
|---|---|
| Getter and traceparent validation | [PERF-012 and propagation map](../components/api/propagation/traceparent/README.md); regex wrapper/groups changes measured in a bundle |
| Optional tracestate | [PERF-013](../components/api/propagation/tracestate/README.md); repeated validation/copying can be avoided for the exact built-in class |
| Dictionary carrier access | [PERF-014](../components/api/propagation/textmap/README.md); custom getters retained in measurement controls |
| Manual parsing | [PERF-015](../components/api/propagation/traceparent/investigations/PERF-015-handrolled-parser-alternatives/notes.md); no winning replacement for optimized regex |
| Immutable context insertion | [Context](../components/api/context/README.md); one-copy experiment rejected |
| Parent lookup and sampling | [PERF-017](../components/sdk/trace/sampling/investigations/PERF-017-parent-context-reuse/notes.md); private handoff remains a prototype |
| Span allocation, scope, and end | Continue with [unsampled](unsampled-span.md) or [sampled](sampled-span.md) flow |

Extraction runs before the recording decision, so its work also applies to
unsampled incoming traces. The propagation bundle measured full extraction in
isolation; no combined incoming-request benchmark joins extraction and the
lifecycle proposals yet.

## Unexplored boundaries

Outgoing injection, baggage, composite propagator overhead, real framework
getters, and an application request profile remain open. Header parsing
correctness includes strict lowercase ASCII hex, zero IDs, suffix rules, optional
space/tab, future versions, and current final-newline acceptance. Preserving
existing behavior is separate from proposing a specification change.
