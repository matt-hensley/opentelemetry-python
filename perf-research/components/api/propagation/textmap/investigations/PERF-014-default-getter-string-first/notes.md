# Check strings before generic iterables in DefaultGetter

ID: PERF-014  
Status: measured  
Implementation: prototype only  
Last reviewed: 2026-10-15

## Hot path and hypothesis

[`DefaultGetter.get`](../../../../../../../opentelemetry-api/src/opentelemetry/propagators/textmap.py#L57) is used by default for mapping-based propagation. It currently tests whether a value is an `Iterable`, then tests whether it is not a string. Since strings are iterable but are returned as a one-element list, checking `str` first may avoid a generic ABC check for common string-valued headers.

Custom getters are user-provided and are not changed by this prototype.

## Baseline and experiment

The temporary method checked `isinstance(val, str)` before the generic iterable check, preserving list conversion for non-string iterables. The extract benchmark included this getter change alongside PERF-012 and PERF-013; there is no isolated getter timing.

See the Python 3.13.14, affinity `[0]`, nine-pair, 0.8-second-target [paired result](../../../../../../../perf-research/evidence/session-2026-10-14-15/artifacts/agent/propagation-audit/paired-extract-comparison.json) and [harness](../../../../../../../perf-research/evidence/session-2026-10-14-15/artifacts/agent/propagation-audit/extract_compare.py).

## Results

The combined prototype reduced CPU 29.1% for the default string getter with no tracestate and 42.1–43.9% with state. The custom list getter cases changed CPU by −28.7% with no state and −39.4% with three entries. Those custom-getter runs do not exercise `DefaultGetter.get`; they show that most of the bundled reduction comes from other changes, but do not quantify this candidate independently. Wall time tracked CPU time.

## Compatibility and validation

For ordinary `str` values, both branch orders return `[val]`; list-like values continue to be copied into a list and other values wrapped. The experiment leaves custom getter implementations alone. Review unusual carrier values with custom `__class__` behavior or virtual ABC registrations before promotion, since the order of `isinstance` checks is observable for such objects.

The combined extraction harness compared span-context fields and tracestate entries for five carrier cases. The later parser corpus also checked context identity, retained data, and getter calls; it did not isolate this getter change. No production `textmap.py` source was changed.

## Decision and next work

Keep as a small candidate with bundled evidence only. Reopen for implementation after an isolated default-getter comparison with string carriers and a small custom-carrier compatibility review. See [PERF-012](../../../traceparent/investigations/PERF-012-regex-wrapper/notes.md) and [PERF-013](../../../tracestate/investigations/PERF-013-tracestate-dict-adoption/notes.md).
