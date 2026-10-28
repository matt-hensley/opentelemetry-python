# Reuse resolved parent context in built-in sampling

ID: PERF-017  
Status: measured  
Implementation: prototype only  
Last reviewed: 2026-10-15

## Hot path and hypothesis

`Tracer.start_span` resolves the parent span context before invoking the sampler. Exact built-in `ParentBased` and built-in delegates then query the same context again to select a delegate and propagate trace state. Reusing the already resolved parent can avoid repeated API context lookup on dropped and sampled child paths. Entry points are `opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py` near line 1208 and `opentelemetry-sdk/src/opentelemetry/sdk/trace/sampling.py` near lines 216, 277, and 342.

## Baseline and experiment

The isolated prototype rewrote the tracer's sampler call for exact `ParentBased`, `StaticSampler`, and `TraceIdRatioBased` instances, falling back to the public sampler methods for other cases. The 9-pair comparison used fixed loops and default random ID generation; functional equivalence checks used fixed IDs. See [paired parent-reuse results](../../../../../../evidence/session-2026-10-14-15/artifacts/agent/lifecycle-audit/paired-parent-reuse-comparison.json) and [prototype source](../../../../../../evidence/session-2026-10-14-15/artifacts/agent/lifecycle-audit/parent_reuse_compare.py).

## Results

Individual CPU results: dropped-root start/end −14.3%, dropped-child start/end −9.6%, and dropped-child current-span −12.4%. For the dropped root/child start/end headline, wall medians were approximately −15.5%/−13.5%. A sampled-child current-span control was only −1.8% CPU, so the observed benefit is concentrated in paths that drop.

In a later combined comparison with API-owned [PERF-016](../../../../../api/trace/scope-management/investigations/PERF-016-generator-wrapper/notes.md), unsampled roots and children improved 25.5% and 23.2% CPU in current-span cases. A separate counted batch-processor run improved 8.7% CPU and 9.8% wall. These are combined incremental results over B2, without PERF-017-only attribution. The earlier uncounted sampled result is excluded: a subsequent default-queue count check lost 1,548 of 10,000 expected spans, making an uncounted comparison unreliable. That later count does not establish the exact loss in the original run.

## Compatibility and validation

The prototype's functional matrix covered valid and invalid parents, local and remote parents, trace-flag combinations, custom sampler delegates, and a `ParentBased` subclass. It preserves subclass dispatch by using exact-type checks. An exact built-in sampler instance can still have an instance-level `should_sample` override; the prototype bypasses that override. This unresolved compatibility question blocks production adoption. A stateful custom runtime context could also return different values across repeated `get_current()` calls, whereas the prototype reuses the first resolution. No production source change is represented by the prototype.

## Decision and next work

Do not land duplicated sampler logic from the prototype. Reopen only with an implementation that preserves instance-level method hooks and runtime-context behavior, plus tests for extension cases and a fresh paired comparison. Keep individual dropped-path evidence distinct from PERF-016 combined and counted processor results.
