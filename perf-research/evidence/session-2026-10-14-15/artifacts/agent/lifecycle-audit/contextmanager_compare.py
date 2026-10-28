"""Compare ordinary scoped span lifecycle with fewer generator-manager layers."""
import argparse
import asyncio
import functools
import gc
import hashlib
import inspect
import json
import statistics
import sys
import textwrap
import time
from pathlib import Path

import psutil
from opentelemetry import context as context_api, trace as trace_api
from opentelemetry.context import Context
from opentelemetry.sdk import trace as sdk
from opentelemetry.sdk.trace import sampling
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult, SimpleSpanProcessor

original = sdk.Tracer.start_as_current_span
source = textwrap.dedent(inspect.getsource(original.__wrapped__))
source = source[source.index("def start_as_current_span("):]
prefix = source[:source.index("    with trace_api.use_span(")]
use_source = textwrap.dedent(inspect.getsource(trace_api.use_span.__wrapped__))
use_body = use_source[use_source.index("    try:\n"):]
use_body = use_body.replace("isinstance(span, Span)", "isinstance(span, trace_api.Span)")
sources = {
    "delegate-generator": prefix + """    yield from _USE_SPAN_GENERATOR(
        span,
        end_on_exit=end_on_exit,
        record_exception=record_exception,
        set_status_on_exception=set_status_on_exception,
    )
""",
    "inline-upper-bound": prefix + use_body,
}
candidates = {"baseline": original}
for name, candidate_source in sources.items():
    namespace = vars(sdk).copy()
    namespace.update(_USE_SPAN_GENERATOR=trace_api.use_span.__wrapped__, _SPAN_KEY=trace_api._SPAN_KEY)
    exec(compile(candidate_source, "<scoped-span-" + name + ">", "exec"), namespace)
    candidates[name] = sdk._agnosticcontextmanager(namespace["start_as_current_span"])

class CapturingExporter(SpanExporter):
    def __init__(self):
        self.spans = []
    def export(self, spans):
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS
    def shutdown(self):
        pass

def check():
    for name, implementation in candidates.items():
        sdk.Tracer.start_as_current_span = implementation
        provider = sdk.TracerProvider(sampler=sampling.ALWAYS_ON, shutdown_on_exit=False)
        exporter = CapturingExporter()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = provider.get_tracer("lifecycle-equivalence")
        token = context_api.attach(Context({"retained": "value"}))
        try:
            starts = []
            original_start = tracer.start_span
            def tracked_start(*args, **kwargs):
                starts.append(None)
                return original_start(*args, **kwargs)
            tracer.start_span = tracked_start
            manager = tracer.start_as_current_span("lazy")
            assert not starts
            assert not exporter.spans
            with manager as span:
                assert len(starts) == 1
                assert span.is_recording()
                assert trace_api.get_current_span() is span
                assert context_api.get_current().get("retained") == "value"
            assert len(exporter.spans) == 1
            assert trace_api.get_current_span() is trace_api.INVALID_SPAN
            with tracer.start_as_current_span("outer") as outer:
                with tracer.start_as_current_span("inner") as inner:
                    assert inner.parent == outer.get_span_context()
                assert trace_api.get_current_span() is outer
            with tracer.start_as_current_span("manual-end", end_on_exit=False) as manual:
                pass
            assert manual.end_time is None
            manual.end()

            @tracer.start_as_current_span("sync-decorator")
            def sync_function():
                return trace_api.get_current_span().get_span_context()
            first, second = sync_function(), sync_function()
            assert first.span_id != second.span_id

            @tracer.start_as_current_span("async-decorator")
            async def async_function():
                before = trace_api.get_current_span()
                await asyncio.sleep(0)
                assert trace_api.get_current_span() is before
                return before.get_span_context()
            assert asyncio.run(async_function()).span_id != asyncio.run(async_function()).span_id

            class ExpectedError(Exception):
                pass
            for exception in (ExpectedError("expected"), StopIteration("stop"), KeyboardInterrupt()):
                try:
                    with tracer.start_as_current_span("error") as error_span:
                        raise exception
                except BaseException as caught:
                    assert caught is exception, (name, type(caught))
                assert error_span.end_time is not None
                if isinstance(exception, Exception):
                    assert error_span.status.status_code is trace_api.StatusCode.ERROR
                    assert len(error_span.events) == 1
                else:
                    assert error_span.status.status_code is trace_api.StatusCode.UNSET
            with tracer.start_as_current_span("ok-after-errors") as clean:
                assert trace_api.get_current_span() is clean
            assert trace_api.get_current_span() is trace_api.INVALID_SPAN
        finally:
            context_api.detach(token)
            provider.shutdown()
    sdk.Tracer.start_as_current_span = original
    print("Lazy entry, nesting, context restore, end flag, sync/async decoration and exception checks passed", flush=True)

def measure(operation, loops):
    operation(1000)
    gc.collect()
    enabled = gc.isenabled()
    gc.disable()
    try:
        cpu_start = time.process_time_ns()
        wall_start = time.perf_counter_ns()
        operation(loops)
        wall = time.perf_counter_ns() - wall_start
        cpu = time.process_time_ns() - cpu_start
    finally:
        if enabled:
            gc.enable()
    return {"loops": loops, "cpu_ns": cpu, "wall_ns": wall}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--seconds", type=float, default=0.7)
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--output", type=Path, default=Path(".agent/lifecycle-audit/paired-contextmanager-comparison.json"))
    args = parser.parse_args()
    try:
        check()
    finally:
        sdk.Tracer.start_as_current_span = original
    if args.check_only:
        return
    parent = trace_api.NonRecordingSpan(trace_api.SpanContext(1, 2, False))
    process = psutil.Process()
    previous = process.cpu_affinity()
    process.cpu_affinity([previous[0]])
    results = []
    try:
        for name, sampler, parent_span, attribute_count in (
            ("dropped-child/current-span", sampling.ParentBased(sampling.ALWAYS_OFF), parent, 0),
            ("sampled-root-4/current-span", sampling.ALWAYS_ON, None, 4),
            ("sampled-root-10/current-span", sampling.ALWAYS_ON, None, 10),
        ):
            provider = sdk.TracerProvider(sampler=sampler, shutdown_on_exit=False)
            tracer = provider.get_tracer("lifecycle-benchmark")
            attributes = {f"key-{index}": f"value-{index}" for index in range(attribute_count)}
            ambient = Context({"retained": "value"})
            if parent_span is not None:
                ambient = trace_api.set_span_in_context(parent_span, ambient)
            token = context_api.attach(ambient)
            try:
                def operation(loops):
                    for _ in range(loops):
                        with tracer.start_as_current_span("benchmark", attributes=attributes):
                            pass
                sdk.Tracer.start_as_current_span = original
                pilot = measure(operation, 10000)
                loops = max(10000, round(10000 * args.seconds * 1e9 / pilot["wall_ns"]))
                samples = []
                names = list(candidates)
                for pair in range(args.repeats):
                    order = names[pair % len(names):] + names[:pair % len(names)]
                    if pair % 2:
                        order.reverse()
                    for mode in order:
                        sdk.Tracer.start_as_current_span = candidates[mode]
                        samples.append({"pair": pair, "mode": mode, **measure(operation, loops)})
                summary = {}
                for mode in names:
                    batches = [sample for sample in samples if sample["mode"] == mode]
                    summary[mode] = {
                        "cpu_ns_op": sum(sample["cpu_ns"] for sample in batches) / sum(sample["loops"] for sample in batches),
                        "wall_ns_op": statistics.median(sample["wall_ns"] / sample["loops"] for sample in batches),
                    }
                    cpu_change = (summary[mode]["cpu_ns_op"] / summary["baseline"]["cpu_ns_op"] - 1) * 100
                    wall_change = (summary[mode]["wall_ns_op"] / summary["baseline"]["wall_ns_op"] - 1) * 100
                    print(f"{name}/{mode}: CPU {cpu_change:+.1f}%, wall {wall_change:+.1f}%", flush=True)
                results.append({"case": name, "summary": summary, "samples": samples})
            finally:
                context_api.detach(token)
                provider.shutdown()
    finally:
        sdk.Tracer.start_as_current_span = original
        process.cpu_affinity(previous)
    paths = [
        Path("opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py"),
        Path("opentelemetry-api/src/opentelemetry/trace/__init__.py"),
        Path("opentelemetry-api/src/opentelemetry/util/_decorator.py"),
    ]
    output = {
        "metadata": {
            "python": sys.version, "pairs": args.repeats, "target_seconds": args.seconds,
            "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "source_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
            "sources": sources,
        },
        "results": results,
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
