# Baggage

**Status: unexplored.** The API baggage propagator lives in [`opentelemetry/baggage/propagation`](../../../../../opentelemetry-api/src/opentelemetry/baggage/propagation/__init__.py). This session did not profile or benchmark baggage extraction/injection, common carrier shapes, serialization, or context updates. No performance claim or optimization proposal is recorded here.

Revisit after collecting a representative API propagation profile and a separate paired benchmark. Preserve custom getter behavior, baggage key/value validation, existing context entries, and header limits.
