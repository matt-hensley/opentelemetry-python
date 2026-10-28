# Share the lock for empty bounded attributes

ID: PERF-009  
Status: deferred  
Implementation: none  
Last reviewed: 2026-10-15

## Hot path and hypothesis

Every `BoundedAttributes` instance allocates a `threading.Lock`, including empty containers. Sharing a lock among empty instances could reduce setup allocations, especially when creating recording spans. Source: `opentelemetry-api/src/opentelemetry/attributes/__init__.py` around `BoundedAttributes.__init__` and mutation methods.

## Baseline and experiment

No timing experiment has been run. No production prototype is retained for shared-lock behavior.

## Results

Unmeasured. A per-instance lock cost has not been isolated from attribute-container initialization or span construction.

## Compatibility and validation

The current non-reentrant lock protects `_dict`, dropped counts, and warning state. Reusing one lock may serialize unrelated objects. A shared lock can deadlock if logging callbacks re-enter attribute operations while the lock is held. Mutating an instance's lock during setup or sharing across aliased/self-referential mappings also needs analysis. A design that switches from shared to private lock must be safe against concurrent first writes and preserve subclass behavior.

## Decision and next work

Defer for correctness and maintainability review before measurement. Reopen only with a lock-lifecycle design that rules out reentrant logging deadlocks and races, then benchmark empty, 1–2 key, and nested attribute cases with CPU and memory evidence.
