# Adopt already parsed tracestate pairs

ID: PERF-013  
Status: measured  
Implementation: prototype only  
Last reviewed: 2026-10-15

## Hot path and hypothesis

When a valid `tracestate` header is present, [`TraceState.from_header`](../../../../../../../opentelemetry-api/src/opentelemetry/trace/span.py#L381) parses each member with `_member_pattern`, stores unique key/value pairs in a local dictionary, then returns `cls(list(pairs.items()))` at line 418. The constructor validates and inserts these parsed values again. The member regex is built from the same `_KEY_FORMAT` and `_VALUE_FORMAT` used by the constructor's validation, and the parser has already rejected duplicate keys.

For the exact built-in `TraceState`, adopting the local dictionary could avoid allocating the intermediate list and repeating validation/reinsertion. The frequency depends on incoming requests that actually carry tracestate.

## Baseline and experiment

The temporary prototype used the local dictionary only for exact `TraceState` instances at or below the 32-entry limit; subclass calls and over-limit data used the original constructor. It initialized a built-in instance, then replaced its private `_dict` with the parsed local mapping. The paired extraction experiment also changed traceparent group access and the default string getter, so no individual PERF-013 number is available.

See the Python 3.13.14, affinity `[0]`, nine-pair, 0.8-second-target [paired result](../../../../../../../perf-research/evidence/session-2026-10-14-15/artifacts/agent/propagation-audit/paired-extract-comparison.json) and [harness](../../../../../../../perf-research/evidence/session-2026-10-14-15/artifacts/agent/propagation-audit/extract_compare.py). Per-case bundled reductions are reported in [PERF-012](../../../traceparent/investigations/PERF-012-regex-wrapper/notes.md).

## Results

The combined prototype reduced CPU by 42.1% for a default getter with one state entry and 43.9% with three entries; wall time changed by −40.1% and −44.4%. A custom list getter with three entries changed by −39.4% CPU and −39.3% wall. These totals include PERF-012 and PERF-014; they cannot be credited to dictionary adoption alone.

## Compatibility and validation

The prototype's exact-type guard avoids changing subclass constructors. Its over-limit fallback preserves the constructor's existing warning and empty-state behavior. The local dictionary is newly created inside `from_header`, preserves insertion order, and is not exposed to the caller. Existing parsing rules still reject invalid members and duplicate keys before adoption.

The combined harness checked resulting span-context fields and ordered state entries. No production `TraceState` source was changed. Remaining review concerns include the maintenance dependency on `_dict` as the storage field, the assumption that the regex and constructor validators remain equivalent, and any future invariants added to `TraceState.__init__`.

## Decision and next work

Retain as a measured prototype, not an implemented change. Reopen after an isolated tracestate-only paired comparison and a compatibility review of private storage and constructor invariants. See [PERF-012](../../../traceparent/investigations/PERF-012-regex-wrapper/notes.md) and [PERF-014](../../../textmap/investigations/PERF-014-default-getter-string-first/notes.md) for the other bundled changes.
