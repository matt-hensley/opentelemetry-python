# PERF-007: Bulk update nonempty bounded attributes

ID: PERF-007  
Status: rejected  
Implementation: none  
Last reviewed: 2026-10-15

## Hot path and hypothesis

`BoundedAttributes._set_items` could merge a cleaned batch into a nonempty dict
through a bulk operation rather than calling the per-key insertion path. Source:
[`BoundedAttributes._set_items`](../../../../../../opentelemetry-api/src/opentelemetry/attributes/__init__.py).

## Baseline and experiment

The prototype was compared against cleaned-dict adoption already enabled, across
disjoint and overlapping updates at 4, 10, and 64 entries. Evidence:
[paired-bulk-comparison.json](../../../../../evidence/session-2026-10-14-15/artifacts/agent/attribute-audit/paired-bulk-comparison.json).
The source and harness hashes and nine paired samples per case are recorded in
the artifact.

## Results

The 4-entry disjoint case changed CPU from roughly 12.23 to 11.89 microseconds,
while the overlapping case regressed from 13.30 to 13.42 microseconds. At 10
entries, disjoint improved from 17.20 to 16.56 microseconds and overlap
regressed from 15.72 to 16.16 microseconds. Larger disjoint batches improved
more, but the optimization is not a consistent win for common small updates.

## Compatibility and validation

The current loop preserves update order, delete/reinsert semantics, overflow
eviction, drop accounting, and subclass `_setitem_locked` hooks. The prototype
would need to reproduce all of these behaviors. No production change was kept.

## Decision and next work

Reject the broad bulk-update path. Reopen only with an approach that wins common
small batches, including overlapping keys, while retaining the ordering and
subclass semantics.
