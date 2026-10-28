# PERF-004: Adopt cleaned dict for empty bounded attributes

ID: PERF-004  
Status: implemented  
Implementation: working tree  
Last reviewed: 2026-10-15

## Hot path and hypothesis

When an empty exact `BoundedAttributes` receives its first cleaned mapping, the
implementation can adopt that newly-created dict instead of inserting each
entry again. This runs for span-constructor attributes and other bulk initial
sets. Source: [`BoundedAttributes._set_items`](../../../../../../opentelemetry-api/src/opentelemetry/attributes/__init__.py).

## Baseline and experiment

The candidate is in the working tree and was compared in paired API attribute
benchmarks. The paired confirmation artifact is
[paired-attribute-confirmation.json](../../../../../evidence/session-2026-10-14-15/artifacts/agent/attribute-audit/paired-attribute-confirmation.json);
the combined follow-up is
[paired-final-confirmation.json](../../../../../evidence/session-2026-10-14-15/artifacts/agent/attribute-audit/paired-final-confirmation.json).
Both are bundled with other API/SDK changes; do not attribute bundle gains to
this candidate alone. Environment, hashes, and raw pairs are in the artifacts.

## Results

The component-mode paired confirmation measured adoption-only CPU per
operation at 11.27 to 10.49 microseconds for four constructor attributes, 13.41
to 12.65 microseconds for ten constructor attributes, and 18.26 to 17.18
microseconds for ten constructor attributes on the current-span path. The
four-attribute `set_attribute` case regressed, so this is not a claim that every
attribute flow improved. A later combined confirmation measured four-attribute
constructor start at about 11.53 to 9.18 microseconds and ten-attribute
constructor start at about 14.30 to 11.29 microseconds; those latter values
combine changes and are not an isolated PERF-004 estimate.

## Compatibility and validation

The fast path is restricted to the exact base type, an empty backing dict, a
cleaned dict, and no overflow under the configured maximum. Subclasses keep the
existing `_setitem_locked` calls; overflow and insertion order stay on the
existing logic. Regression tests cover subclass hooks, zero and finite limits,
cleaning, ordering, and dropped counts. See the archived attribute test log.

## Decision and next work

Retain the narrow fast path. The root evidence ledger records the working-tree
status; it is not a merged result. Revisit only if further cross-version tests
show a compatibility regression or materially different performance.
