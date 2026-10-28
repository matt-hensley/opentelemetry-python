# PERF-008: Specialize bounded-attribute construction

ID: PERF-008  
Status: rejected  
Implementation: none  
Last reviewed: 2026-10-15

## Hot path and hypothesis

Attribute cleaning and insertion are used for initial span attributes. A
constructor-specific implementation might avoid some general mapping work.
Source: [`BoundedAttributes.__init__`](../../../../../../opentelemetry-api/src/opentelemetry/attributes/__init__.py).

## Baseline and experiment

The constructor specialization prototype was compared to the cleaned-dict
adoption baseline with empty, four-value, and ten-value string and mixed-value
cases. Evidence:
[paired-ctor-comparison.json](../../../../../evidence/session-2026-10-14-15/artifacts/agent/attribute-audit/paired-ctor-comparison.json).
Nine paired samples and source hashes are recorded there.
The batches used 50,000 operations and often lasted only about 0.28–0.66 seconds.
Windows CPU quantization weakens this small signal. The harness was saved after
measurement, so its provenance is weaker than the later paired studies.

## Results

The median CPU changes were 0% for empty input, about 0–3.45% for four values,
and 0–2.94% for ten values, depending on value shape. The signal was small and
inconsistent; it does not justify a second construction path.

## Compatibility and validation

Constructor specialization duplicates cleaning, limit, coercion, and dropped
count behavior. The prototype was not retained. The current constructor tests
remain the regression baseline.

## Decision and next work

Reject. Reopen only with stronger isolated evidence and a design that does not
duplicate validation and limit semantics.
