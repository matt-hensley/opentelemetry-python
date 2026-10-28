# PERF-016: Share the use_span generator body

ID: PERF-016  
Status: measured  
Implementation: prototype only  
Last reviewed: 2026-10-15

## Hot path and hypothesis

SDK `Tracer.start_as_current_span` is an agnostic generator context manager that
enters API `use_span`, itself another agnostic context manager. A private typed
generator shared by both entry points could let the SDK `yield from` the attach,
detach, exception, and end implementation, removing one context-manager wrapper
without duplicating cleanup semantics. Sources: [`SDK start_as_current_span`](../../../../../../../opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py)
and [`API use_span`](../../../../../../../opentelemetry-api/src/opentelemetry/trace/__init__.py).

## Baseline and experiment

A delegate-generator prototype and an inline duplicated-body upper bound were
compared to baseline. Evidence:
[paired-contextmanager-comparison.json](../../../../../../evidence/session-2026-10-14-15/artifacts/agent/lifecycle-audit/paired-contextmanager-comparison.json).
Source hashes, environment, and nine paired samples are recorded in the
artifact; the benchmark exercises dropped and sampled current-span flows.

## Results

The shared delegate prototype reduced dropped-child current-span CPU by about
11.5%, sampled root with four attributes by about 5.6%, and sampled root with
ten attributes by about 9.9%. The inline upper bound was not consistently
faster than delegation and duplicates exception/cleanup logic. This is a
prototype result, not a source implementation result.

## Compatibility and validation

The generator boundary must preserve laziness, sync and async use through
`_agnosticcontextmanager`, exception injection, detach on all exits, optional
`end_on_exit`, and public signatures/names. No production source change is
retained. The prototype preflight checked lazy entry, nested parent selection,
context restoration, the end flag, sync/async decorator reuse with fresh IDs,
and exception identity/cleanup for Exception, StopIteration, and KeyboardInterrupt.
Async cancellation and concurrent use still need coverage. The API and SDK
regression suites must be run after implementation.

## Decision and next work

Measured and worth a narrowly scoped production implementation. Prefer a single private typed
generator containing the existing API body; keep both public agnostic wrappers
and have SDK delegate with `yield from`. Validate sync/async, exception, and
typing behavior in that implementation, then repeat the paired lifecycle comparison.
