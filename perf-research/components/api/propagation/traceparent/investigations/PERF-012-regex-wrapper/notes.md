# Avoid regex wrapper and repeated group retrieval

ID: PERF-012  
Status: measured  
Implementation: prototype only  
Last reviewed: 2026-10-15

## Hot path and hypothesis

Each successful inbound extraction calls `re.search` with an already compiled pattern at [`tracecontext.py:45`](../../../../../../../opentelemetry-api/src/opentelemetry/trace/propagation/tracecontext.py#L45), then calls `Match.group` separately for fields at lines 49–52 and again for the optional suffix at line 58. Calling the compiled pattern's `.search()` method directly and retrieving `match.groups()` once may remove wrapper and repeated method dispatch on the common accepted-header path.

This is an API propagation path used per inbound request. The hypothesis concerns only the wrapper and group access; the compiled regex remains responsible for all accepted/rejected forms.

## Baseline and experiment

The baseline is the checked-out API source snapshot whose SHA-256 hashes are recorded in the archived extract result. The temporary prototype used direct compiled-pattern `.search()` and one groups tuple. The paired harness also enabled the PERF-013 TraceState dictionary path and PERF-014 string-first getter, so its result is bundled, not an individual PERF-012 comparison.

The run used Python 3.13.14, process affinity `[0]`, nine alternating pairs, and a target batch of 0.8 seconds. Setup and correctness fingerprinting were outside timed batches. See the [paired result](../../../../../../../perf-research/evidence/session-2026-10-14-15/artifacts/agent/propagation-audit/paired-extract-comparison.json) and [harness](../../../../../../../perf-research/evidence/session-2026-10-14-15/artifacts/agent/propagation-audit/extract_compare.py).

## Results

| Input shape | Baseline CPU | Combined CPU | CPU change | Wall change |
| --- | ---: | ---: | ---: | ---: |
| Default getter, no state | 3.203 µs | 2.270 µs | −29.1% | −31.4% |
| Default getter, one state entry | 6.035 µs | 3.494 µs | −42.1% | −40.1% |
| Default getter, three state entries | 7.598 µs | 4.262 µs | −43.9% | −44.4% |
| Custom list getter, no state | 3.199 µs | 2.280 µs | −28.7% | −26.9% |
| Custom list getter, three state entries | 6.996 µs | 4.242 µs | −39.4% | −39.3% |

These are combined PERF-012/013/014 results. They do not identify PERF-012's standalone contribution. The later parser comparison used the optimized regex prototype as its baseline; it does not isolate this change against the original extractor.

## Compatibility and validation

Direct `.search()` preserves the compiled pattern object, anchors, and matching behavior. `match.groups()` returns the same captured strings and optional `None` suffix as the existing individual group calls. The extractor must continue to read only `header[0]`, reject zero IDs, reject suffixes for version `00`, reject version `ff`, preserve future-version handling, and avoid asking the getter for tracestate after an invalid traceparent.

The combined extraction harness compared trace ID, span ID, flags, remote status, and tracestate entries for its five carrier cases. The later 11,770-header parser corpus additionally checked context identity, retained context data, and getter-call sequence; it did not isolate PERF-012 timing. No production tracecontext source was changed. Check subclass/private regex overrides before promoting any specialization that bypasses the instance's configured compiled pattern.

## Decision and next work

Keep as a measured candidate, not an accepted standalone optimization. Reopen for implementation only after an isolated paired comparison shows a stable improvement and source-level compatibility review confirms any custom regex override behavior. See [PERF-015](../PERF-015-handrolled-parser-alternatives/notes.md) for rejected parser rewrites and [PERF-013](../../../tracestate/investigations/PERF-013-tracestate-dict-adoption/notes.md) and [PERF-014](../../../textmap/investigations/PERF-014-default-getter-string-first/notes.md) for the other members of the measured bundle.
