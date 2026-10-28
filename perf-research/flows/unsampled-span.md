# Unsampled span lifecycle

This is the ordinary dropped root or child flow under ParentBased sampling,
including entry and exit of a current-span scope.

~~~mermaid
flowchart LR
  A[Current parent] --> B[Tracer start]
  B --> C[Root ID or inherited trace ID]
  C --> D[ParentBased delegate]
  D --> E[SpanContext and NonRecordingSpan]
  E --> F[Attach current context]
  F --> G[Application body]
  G --> H[Detach and no-op end]
~~~

| Stage | Candidate and status |
|---|---|
| Current span retrieval | [PERF-001](../components/api/trace/span-context/investigations/PERF-001-current-span-lookup/notes.md), retained working-tree implementation |
| Decision check | [PERF-002](../components/sdk/trace/sampling/investigations/PERF-002-decision-recording/notes.md), retained working-tree implementation |
| Repeated parent lookup | [PERF-017](../components/sdk/trace/sampling/investigations/PERF-017-parent-context-reuse/notes.md), measured prototype |
| Context copy | [PERF-003](../components/api/context/investigations/PERF-003-context-copy/notes.md), rejected |
| Two nested context-manager wrappers | [PERF-016](../components/api/trace/scope-management/investigations/PERF-016-generator-wrapper/notes.md), measured shared-generator prototype |
| Flags and empty sampling attributes | Sibling perf-audit worktree handoff; check ownership before investigating |

The combined PERF-016/017 prototype reduced CPU 25.5% for root scopes and 23.2%
for child scopes relative to the already optimized retained worktree. This is
an incremental comparison. It does not establish a cumulative baseline-to-final
SDK reduction.

## Contracts and remaining work

Preserve deferred span creation, parent semantics, context restoration, custom
sampler dispatch, sync/async decorator reuse, exception identity, and end-on-exit.
A disabled tracer is a separate path, not equivalent to a sampler returning DROP.
Stateful runtime plugins and instance-level sampler overrides still need a safe
production design for the parent-reuse proposal.

The historical dropped profile shows repeated lookups and wrapper construction.
Refresh the profile after implementation rather than applying its old cost
fractions to the current tree. No recorded-span attribute or event/link savings
are attributed to this flow.
