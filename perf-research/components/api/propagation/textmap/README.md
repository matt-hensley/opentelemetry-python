# Text map

The default getter in [`textmap.py`](../../../../../opentelemetry-api/src/opentelemetry/propagators/textmap.py#L57) reads a value from a mapping and returns it as a list. For strings, the current path first checks `Iterable` and then excludes `str`, even though the final result is a one-element list in either case. Custom getters implement the same interface and remain application-controlled.

[`PERF-014`](investigations/PERF-014-default-getter-string-first/notes.md) records a prototype that checks strings before the generic iterable branch. Its performance contribution was not isolated from the traceparent and tracestate changes.
