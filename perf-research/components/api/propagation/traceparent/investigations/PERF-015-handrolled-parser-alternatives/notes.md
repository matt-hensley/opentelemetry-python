# Hand-written traceparent parser alternatives

ID: PERF-015  
Status: rejected  
Implementation: prototype only  
Last reviewed: 2026-10-15

## Hot path and hypothesis

The current regex parses a full traceparent in [`TraceContextTextMapPropagator.extract`](../../../../../../../opentelemetry-api/src/opentelemetry/trace/propagation/tracecontext.py#L24). A fixed-position parser for the common 55-character version-`00` record might avoid regex machinery. The prototype restricted that fast path to exact `str` values with the expected length, prefix, and separator positions, then fell back to the current regex for every other form.

## Baseline and experiment

The baseline was the optimized-regex prototype used in PERF-012 (compiled pattern `.search()` plus one `match.groups()` call). Four fast-path variants were compared: ASCII/lowercase string checks plus `int`, `str.translate` allowlist, a character loop, and a fused Python hex-conversion loop. A follow-up compared `str.strip` allowlist validation.

The differential corpus compared each parser against the checked-out extractor for 11,770 headers and checked returned context identity, retained context data, getter-call order, and span-context fields. The 5-parser run used Python 3.13.14, affinity `[0]`, seven alternating rounds, and a 0.6-second target per batch. The strip follow-up used nine rounds and a 0.9-second target. See the [paired parser result](../../../../../../../perf-research/evidence/session-2026-10-14-15/artifacts/agent/propagation-audit/paired-parser-comparison.json), [parser harness](../../../../../../../perf-research/evidence/session-2026-10-14-15/artifacts/agent/propagation-audit/parser_compare.py), [strip result](../../../../../../../perf-research/evidence/session-2026-10-14-15/artifacts/agent/propagation-audit/paired-strip-comparison.json), and [strip harness](../../../../../../../perf-research/evidence/session-2026-10-14-15/artifacts/agent/propagation-audit/strip_compare.py).

## Results

CPU change versus optimized regex (negative would be faster):

| Parser | Default, no state | Custom lists, no state | Custom lists, three state entries |
| --- | ---: | ---: | ---: |
| Native string checks + `int` | 0.0% | +3.7% | +0.4% |
| `translate` allowlist + `int` | +4.0% | +9.6% | +0.7% |
| Character-validation loop + `int` | +54.7% | +57.2% | +28.4% |
| Fused Python hex-conversion loop | +156.9% | +156.9% | +80.2% |
| `strip` allowlist + `int` (follow-up) | +8.6% | +11.6% | +4.8% |

Wall results agreed in direction. None of the hand-written variants produced a robust win over the optimized regex. The native checks were approximately tied in the default no-state case and slower in custom-getter cases; they were not a clear improvement.

## Compatibility and validation

The fallback is required for outer SP/HTAB, final-newline behavior of the regex `$` anchor, non-`00` versions, optional version extensions, and all malformed shapes. A parser must also keep lowercase-only ASCII hex, exact component widths and separators, nonzero IDs, unrestricted two-digit flags, the rule that version `00` rejects a suffix, and version `ff` rejection. `int(..., 16)` alone accepts forms the regex rejects, so it cannot serve as validation.

The corpus covers whitespace, uppercase/non-ASCII characters, changes and length edits at each position, version/suffix forms, flag values, zero IDs, and generated headers. The hand-written fast path can bypass a subclass's override of the private compiled regex for a canonical record unless guarded; keep this extension caveat visible if revisited. No production tracecontext source was changed.

## Decision and next work

Reject these parser alternatives for now. Reopen only if a simpler native-string formulation beats the optimized regex by a stable margin in isolated paired runs and passes a broader differential suite, including subclass/private-pattern behavior. The regex-plus-groups candidate is tracked separately in [PERF-012](../PERF-012-regex-wrapper/notes.md).
