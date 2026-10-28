# API propagation

Propagation extracts and injects context at process boundaries. This subtree tracks API-side header work only; instrumentation and exporters are out of scope. The common extraction path starts in [`TraceContextTextMapPropagator.extract`](../../../../opentelemetry-api/src/opentelemetry/trace/propagation/tracecontext.py#L27), reads `traceparent`, optionally parses `tracestate`, then returns a context containing a remote non-recording span.

## Components

- [Traceparent](traceparent/README.md): compiled W3C header validation and span-context construction.
- [Tracestate](tracestate/README.md): member parsing, validation, and mapping construction.
- [Text map](textmap/README.md): default carrier getters and setter interfaces.
- [Baggage](baggage/README.md): propagation path recorded as unexplored.

## Investigations

| ID | Owner | Finding |
| --- | --- | --- |
| [PERF-012](traceparent/investigations/PERF-012-regex-wrapper/notes.md) | Traceparent | Compiled regex method dispatch and repeated match-group retrieval are a measured candidate within a combined prototype; individual gain is unknown. |
| [PERF-013](tracestate/investigations/PERF-013-tracestate-dict-adoption/notes.md) | Tracestate | Parsed pairs can potentially avoid constructor revalidation and reinsertion for the exact built-in type. Only bundled evidence exists. |
| [PERF-014](textmap/investigations/PERF-014-default-getter-string-first/notes.md) | Text map | Check strings before the generic iterable path; only bundled evidence exists. |
| [PERF-015](traceparent/investigations/PERF-015-handrolled-parser-alternatives/notes.md) | Traceparent | Several hand-written valid-version-00 parsers were differentially checked and measured; none beat the optimized regex candidate. |

The five-case extract comparison reports a 28.7–43.9% CPU reduction for the combined PERF-012/013/014 prototype. It does not isolate those changes, so the result must not be attributed to any single investigation. See each note for the exact workload and limitations.
