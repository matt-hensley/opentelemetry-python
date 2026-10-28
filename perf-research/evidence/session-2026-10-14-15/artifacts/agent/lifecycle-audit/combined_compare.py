"""Confirm combined hot-path savings, including a configured batch processor."""
import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path

import parent_reuse_compare as parent
import contextmanager_compare as manager
from opentelemetry import context as context_api, trace as trace_api
from opentelemetry.context import Context
from opentelemetry.sdk import trace as sdk
from opentelemetry.sdk.trace import sampling
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult

class DiscardExporter(SpanExporter):
    def export(self, spans):
        return SpanExportResult.SUCCESS
    def shutdown(self):
        pass

def install(combined):
    sdk.Tracer.start_span = parent.candidate if combined else parent.original
    sdk.Tracer.start_as_current_span = manager.candidates["delegate-generator"] if combined else manager.original

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=0.9)
    parser.add_argument("--repeats", type=int, default=9)
    args = parser.parse_args()
    process = manager.psutil.Process()
    previous = process.cpu_affinity()
    process.cpu_affinity([previous[0]])
    results = []
    try:
        for name, parent_span, sampled, with_processor in (
            ("dropped-root/current-span", None, False, False),
            ("dropped-child/current-span", trace_api.NonRecordingSpan(trace_api.SpanContext(11, 13, False)), False, False),
            ("sampled-remote-child-4/batch-processor", trace_api.NonRecordingSpan(trace_api.SpanContext(11, 13, True, trace_api.TraceFlags(1))), True, True),
        ):
            provider = sdk.TracerProvider(sampler=sampling.ParentBased(sampling.ALWAYS_ON if sampled else sampling.TraceIdRatioBased(0)), shutdown_on_exit=False)
            if with_processor:
                provider.add_span_processor(BatchSpanProcessor(DiscardExporter()))
            tracer = provider.get_tracer("combined-hot-paths")
            attributes = {f"key-{index}": f"value-{index}" for index in range(4)} if sampled else {}
            ambient = Context({"retained": "value"})
            if parent_span is not None:
                ambient = trace_api.set_span_in_context(parent_span, ambient)
            token = context_api.attach(ambient)
            try:
                def operation(loops):
                    for _ in range(loops):
                        with tracer.start_as_current_span("benchmark", attributes=attributes):
                            pass
                    # Include queue drain so CPU from this batch stays in its mode.
                    if with_processor:
                        assert provider.force_flush()
                install(False)
                pilot = manager.measure(operation, 10000)
                loops = max(10000, round(10000 * args.seconds * 1e9 / pilot["wall_ns"]))
                samples = []
                for pair in range(args.repeats):
                    order = ("baseline", "combined") if pair % 2 == 0 else ("combined", "baseline")
                    for mode in order:
                        install(mode == "combined")
                        samples.append({"pair": pair, "mode": mode, **manager.measure(operation, loops)})
                summary = {}
                for mode in ("baseline", "combined"):
                    batches = [sample for sample in samples if sample["mode"] == mode]
                    summary[mode] = {
                        "cpu_ns_op": sum(sample["cpu_ns"] for sample in batches) / sum(sample["loops"] for sample in batches),
                        "wall_ns_op": statistics.median(sample["wall_ns"] / sample["loops"] for sample in batches),
                    }
                changes = {key: (summary["combined"][key] / summary["baseline"][key] - 1) * 100 for key in ("cpu_ns_op", "wall_ns_op")}
                print(f"{name}: CPU {changes['cpu_ns_op']:+.1f}%, wall {changes['wall_ns_op']:+.1f}%", flush=True)
                results.append({"case": name, "loops_per_batch": loops, "summary": summary, "change_percent": changes, "samples": samples})
            finally:
                context_api.detach(token)
                provider.shutdown()
    finally:
        install(False)
        process.cpu_affinity(previous)
    output = {
        "metadata": {
            "python": sys.version,
            "pairs": args.repeats,
            "target_seconds": args.seconds,
            "sources": {
                str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in map(Path, [
                    __file__, parent.__file__, manager.__file__,
                    "opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py",
                    "opentelemetry-sdk/src/opentelemetry/sdk/trace/sampling.py",
                    "opentelemetry-api/src/opentelemetry/trace/__init__.py",
                ])
            },
            "batch_note": "Default BatchSpanProcessor and no-I/O exporter. Queue flush included in measured batch.",
        },
        "results": results,
    }
    Path(".agent/lifecycle-audit/paired-combined-comparison.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
