# Traceparent

The [W3C trace-context propagator](../../../../../opentelemetry-api/src/opentelemetry/trace/propagation/tracecontext.py#L19) reads only the first value returned by its getter. Its compiled pattern validates the full header shape, including outer SP/HTAB, lowercase hex fields, optional version extension, and the special `00`/`ff` rules. Accepted IDs and flags are converted before a remote `SpanContext` is made.

The ordinary inbound path is a hot per-request candidate. [`PERF-012`](investigations/PERF-012-regex-wrapper/notes.md) evaluates avoiding the `re.search` wrapper and repeated `Match.group` calls while keeping the same compiled regex. [`PERF-015`](investigations/PERF-015-handrolled-parser-alternatives/notes.md) records rejected hand-written parsers and the validation hazards they must preserve.

These are research prototypes only. No tracecontext production source change was made for these investigations. The combined extraction result cannot establish the individual value of PERF-012.
