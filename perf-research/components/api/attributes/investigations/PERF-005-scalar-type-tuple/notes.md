# PERF-005: Reuse scalar type tuple during attribute cleaning

ID: PERF-005  
Status: implemented  
Implementation: working tree  
Last reviewed: 2026-10-15

## Hot path and hypothesis

Recursive attribute cleaning performs an `isinstance` check for common scalar
types. A tuple literal in that check is rebuilt as part of the function path;
binding it once at module scope avoids repeated tuple construction. Source:
[`_clean_attribute_value`](../../../../../../opentelemetry-api/src/opentelemetry/attributes/__init__.py).

## Baseline and experiment

The isolated scalar-cleaning comparison is
[paired-cleaner-comparison.json](../../../../../evidence/session-2026-10-14-15/artifacts/agent/attribute-audit/paired-cleaner-comparison.json).
The change also appears in the current API working tree. Paired follow-up evidence is archived in
[paired-attribute-confirmation.json](../../../../../evidence/session-2026-10-14-15/artifacts/agent/attribute-audit/paired-attribute-confirmation.json)
and
[paired-final-confirmation.json](../../../../../evidence/session-2026-10-14-15/artifacts/agent/attribute-audit/paired-final-confirmation.json).
The comparisons include other candidates, so they are not an isolated estimate
of PERF-005.

## Results

The isolated comparison measured approximately 3.8% lower CPU for four string
values, 0.8% for ten strings, and 4.4% for ten mixed values; empty input was
effectively flat. These are modest results from the archived workload. Scalar
identity behavior is also tested for builtin and subclass values. Follow-up
bundles do not isolate this candidate, so do not attribute their full gains to
PERF-005.

## Compatibility and validation

The tuple contains the same accepted scalar classes as before; only its
lifetime changes. Existing cleaning behavior and scalar identity are covered by
the API attribute tests. See the archived attribute test log.

## Decision and next work

Retain the module constant as a minimal change. If isolated attribution is
needed, compare it independently with current attribute adoption held fixed.
