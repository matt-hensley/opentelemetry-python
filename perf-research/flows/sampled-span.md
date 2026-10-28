# Sampled span lifecycle

Follow a successful root or child span with four or ten string attributes, with
no events or links unless explicitly noted.

~~~mermaid
flowchart LR
  A[Parent lookup and sampling] --> B[SpanContext]
  B --> C[Span and attributes]
  C --> D[Current context scope]
  D --> E[Application body and mutations]
  E --> F[End and freeze]
  F --> G[ReadableSpan]
  G --> H[Processor and exporter]
~~~

| Stage | Coverage |
|---|---|
| Sampling | [Sampling map](../components/sdk/trace/sampling/README.md); parent reuse measured, custom handoff pending |
| Attribute cleaning and storage | [Attributes](../components/api/attributes/README.md); PERF-004/005 retained; bulk update and constructor variants rejected |
| Empty event/link containers | [PERF-006](../components/sdk/trace/span-creation/investigations/PERF-006-lazy-events-links/notes.md), retained implementation |
| Context activation | [PERF-016](../components/api/trace/scope-management/investigations/PERF-016-generator-wrapper/notes.md), measured shared-generator prototype |
| Incremental writes and locks | [PERF-009](../components/sdk/shared/bounded-collections/investigations/PERF-009-shared-attribute-lock/notes.md), deferred synchronization design |
| Freezing and readable view | [Span ending](../components/sdk/trace/span-ending/README.md); view caching is unmeasured and deferred |
| Batch handoff | [Processors](../components/sdk/trace/processors/README.md); counted combined confirmation includes no-I/O export and queue drain |

The retained attribute/scalar/storage bundle reduced sampled start/end CPU by
20.4–21.1% in the selected 4/10-attribute cases, and current-scope CPU by 12.6%
with ten attributes. Empty event/link storage saved about 1,824 retained traced
bytes per live span in the measured cohorts.

The newer shared-generator and parent-reuse prototypes together saved 8.7% CPU
and 9.8% wall time for a sampled remote child with four attributes and a batch
processor. That counted run used queue capacity 131072 and an exporter without
I/O, with every batch drained and requested/exported counts equal. The initial
uncounted sampled result is excluded.

## Unknowns

A cumulative comparison joining all proposed changes is still open. Exporter
serialization/networking, application workload mix, native dependencies, and
instrumentation overhead have not been optimized in this investigation.
Memory/RSS, GC behavior and latency under a real request rate need separate
measurements. The recorded tracemalloc reduction is not an RSS or allocation
count measurement.

Preserve zero-capacity drops, bounded eviction order, callback-time mutation,
immutable snapshots, and first concurrent event/link additions when changing
storage or end behavior.
