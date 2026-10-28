"""Measure reusing the already resolved parent with exact built-in ParentBased."""
import argparse
import hashlib
import inspect
import json
import statistics
import sys
import textwrap
from pathlib import Path

import contextmanager_compare as harness
from opentelemetry import trace as trace_api, context as context_api
from opentelemetry.context import Context
from opentelemetry.sdk import trace as sdk
from opentelemetry.sdk.trace import sampling
from opentelemetry.sdk.trace.id_generator import IdGenerator

def sample_parent(sampler, parent, parent_context, trace_id, name, kind, attributes, links):
    delegate = sampler._root
    if parent is not None and parent.is_valid:
        if parent.is_remote:
            delegate = sampler._remote_parent_sampled if parent.trace_flags.sampled else sampler._remote_parent_not_sampled
        else:
            delegate = sampler._local_parent_sampled if parent.trace_flags.sampled else sampler._local_parent_not_sampled
    if type(delegate) is sampling.StaticSampler:
        decision = delegate._decision
    elif type(delegate) is sampling.TraceIdRatioBased:
        decision = sampling.Decision.RECORD_AND_SAMPLE if trace_id & delegate.TRACE_ID_LIMIT < delegate.bound else sampling.Decision.DROP
    else:
        return delegate.should_sample(parent_context=parent_context, trace_id=trace_id, name=name, kind=kind, attributes=attributes, links=links)
    state = parent.trace_state if parent is not None and parent.is_valid else None
    return sampling.SamplingResult(decision, None if decision is sampling.Decision.DROP else attributes, state)

original = sdk.Tracer.start_span
source = textwrap.dedent(inspect.getsource(original))
source = source[source.index("def start_span("):]
target = "    sampling_result = self.sampler.should_sample(context, trace_id, name, kind, attributes, links)"
replacement = """    if type(self.sampler) is sampling.ParentBased:
        sampling_result = _SAMPLE_PARENT(self.sampler, parent_span_context, context, trace_id, name, kind, attributes, links)
    else:
        sampling_result = self.sampler.should_sample(context, trace_id, name, kind, attributes, links)"""
assert target in source
source = source.replace(target, replacement)
namespace = vars(sdk).copy()
namespace["_SAMPLE_PARENT"] = sample_parent
exec(compile(source, "<parent-reuse-start-span>", "exec"), namespace)
candidate = namespace["start_span"]

class FixedIds(IdGenerator):
    def generate_span_id(self):
        return 17
    def generate_trace_id(self):
        return 19

class CustomSampler(sampling.Sampler):
    _state = trace_api.TraceState([("custom", "state")])
    def should_sample(self, *args, **kwargs):
        return sampling.SamplingResult(sampling.Decision.RECORD_AND_SAMPLE, {"custom": "yes"}, self._state)
    def get_description(self):
        return "CustomSampler"

class CustomParentBased(sampling.ParentBased):
    def should_sample(self, *args, **kwargs):
        return sampling.SamplingResult(sampling.Decision.DROP)

def check():
    state = trace_api.TraceState([("vendor", "value")])
    parents = [None]
    for remote in (False, True):
        for flags in (0, 1, 2, 3):
            parents.append(trace_api.NonRecordingSpan(trace_api.SpanContext(11, 13, remote, trace_api.TraceFlags(flags), state)))
    parents.append(trace_api.NonRecordingSpan(trace_api.SpanContext(0, 0, True, trace_api.TraceFlags(1), state)))
    count = 0
    for sampler in (
        sampling.ParentBased(sampling.ALWAYS_OFF), sampling.ParentBased(sampling.ALWAYS_ON),
        sampling.ParentBased(sampling.TraceIdRatioBased(0)), sampling.ParentBased(sampling.TraceIdRatioBased(0.5)),
        sampling.ParentBased(CustomSampler(), remote_parent_sampled=CustomSampler(), local_parent_not_sampled=CustomSampler()),
        sampling.ALWAYS_ON, sampling.ALWAYS_OFF, CustomSampler(), CustomParentBased(sampling.ALWAYS_ON),
    ):
        provider = sdk.TracerProvider(sampler=sampler, id_generator=FixedIds(), shutdown_on_exit=False)
        tracer = provider.get_tracer("reuse-equivalence")
        try:
            for parent in parents:
                context = Context({"retained": "value"})
                if parent is not None:
                    context = trace_api.set_span_in_context(parent, context)
                def fingerprint(implementation):
                    sdk.Tracer.start_span = implementation
                    span = tracer.start_span("check", context=context, attributes={"input": "value"})
                    sc = span.get_span_context()
                    result = (sc.trace_id, sc.span_id, sc.trace_flags, sc.is_remote, tuple(sc.trace_state.items()), span.is_recording())
                    if span.is_recording():
                        result += (tuple(span.attributes.items()), span.parent)
                    span.end()
                    return result
                assert fingerprint(original) == fingerprint(candidate), (type(sampler), parent)
                count += 1
        finally:
            provider.shutdown()
    sdk.Tracer.start_span = original
    print(f"Parent reuse: {count} built-in/custom sampler and parent combinations agree", flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--seconds", type=float, default=0.8)
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--output", type=Path, default=Path(".agent/lifecycle-audit/paired-parent-reuse-comparison.json"))
    args = parser.parse_args()
    try:
        check()
    finally:
        sdk.Tracer.start_span = original
    if args.check_only:
        return
    process = harness.psutil.Process()
    previous = process.cpu_affinity()
    process.cpu_affinity([previous[0]])
    results = []
    off_parent = trace_api.NonRecordingSpan(trace_api.SpanContext(11, 13, False))
    on_parent = trace_api.NonRecordingSpan(trace_api.SpanContext(11, 13, False, trace_api.TraceFlags(1)))
    cases = [
        ("dropped-root/start-end", sampling.ParentBased(sampling.TraceIdRatioBased(0)), None, False, 0),
        ("dropped-child/start-end", sampling.ParentBased(sampling.TraceIdRatioBased(0)), off_parent, False, 0),
        ("dropped-child/current-span", sampling.ParentBased(sampling.TraceIdRatioBased(0)), off_parent, True, 0),
        ("sampled-child-4/current-span", sampling.ParentBased(sampling.ALWAYS_ON), on_parent, True, 4),
        ("static-off-control/start-end", sampling.ALWAYS_OFF, off_parent, False, 0),
        ("custom-control/start-end", CustomSampler(), None, False, 0),
    ]
    try:
        for label, sampler, parent, scoped, attribute_count in cases:
            provider = sdk.TracerProvider(sampler=sampler, shutdown_on_exit=False)
            tracer = provider.get_tracer("parent-reuse-benchmark")
            attrs = {f"key-{index}": f"value-{index}" for index in range(attribute_count)}
            ambient = Context({"retained": "value"})
            if parent is not None:
                ambient = trace_api.set_span_in_context(parent, ambient)
            token = context_api.attach(ambient)
            try:
                if scoped:
                    def operation(loops):
                        for _ in range(loops):
                            with tracer.start_as_current_span("benchmark", attributes=attrs):
                                pass
                else:
                    def operation(loops):
                        for _ in range(loops):
                            tracer.start_span("benchmark", attributes=attrs).end()
                sdk.Tracer.start_span = original
                pilot = harness.measure(operation, 10000)
                loops = max(10000, round(10000 * args.seconds * 1e9 / pilot["wall_ns"]))
                samples = []
                for pair in range(args.repeats):
                    order = ("baseline", "reuse-parent") if pair % 2 == 0 else ("reuse-parent", "baseline")
                    for mode in order:
                        sdk.Tracer.start_span = original if mode == "baseline" else candidate
                        samples.append({"pair": pair, "mode": mode, **harness.measure(operation, loops)})
                summary = {}
                for mode in ("baseline", "reuse-parent"):
                    batches = [sample for sample in samples if sample["mode"] == mode]
                    summary[mode] = {
                        "cpu_ns_op": sum(sample["cpu_ns"] for sample in batches) / sum(sample["loops"] for sample in batches),
                        "wall_ns_op": statistics.median(sample["wall_ns"] / sample["loops"] for sample in batches),
                    }
                cpu_change = (summary["reuse-parent"]["cpu_ns_op"] / summary["baseline"]["cpu_ns_op"] - 1) * 100
                wall_change = (summary["reuse-parent"]["wall_ns_op"] / summary["baseline"]["wall_ns_op"] - 1) * 100
                print(f"{label}: CPU {cpu_change:+.1f}%, wall {wall_change:+.1f}%", flush=True)
                results.append({"case": label, "summary": summary, "samples": samples})
            finally:
                context_api.detach(token)
                provider.shutdown()
    finally:
        sdk.Tracer.start_span = original
        process.cpu_affinity(previous)
    paths = [
        Path("opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py"),
        Path("opentelemetry-sdk/src/opentelemetry/sdk/trace/sampling.py"),
    ]
    output = {
        "metadata": {
            "python": sys.version, "pairs": args.repeats,
            "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "source_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
            "candidate": source, "sampling_helper": inspect.getsource(sample_parent),
        },
        "results": results,
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
