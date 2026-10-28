"""Profile current tracing code on ordinary dropped or sampled nested scopes."""

import argparse
import cProfile
import hashlib
import json
import platform
import pstats
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from opentelemetry.sdk.trace import TracerProvider, sampling

RESEARCH = Path(__file__).resolve().parents[1]
ROOT = RESEARCH.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("dropped", "sampled"), required=True)
    parser.add_argument("--loops", type=int, default=100000)
    args = parser.parse_args()
    if args.loops <= 0:
        parser.error("--loops must be positive")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = RESEARCH / ".runs" / f"{stamp}-profile-{args.scenario}-{uuid.uuid4().hex[:8]}"
    destination.mkdir(parents=True, exist_ok=False)
    sampler = sampling.ParentBased(sampling.TraceIdRatioBased(0) if args.scenario == "dropped" else sampling.ALWAYS_ON)
    provider = TracerProvider(sampler=sampler, shutdown_on_exit=False)
    tracer = provider.get_tracer("performance-research-profile")
    attributes = {f"key-{index}": f"value-{index}" for index in range(4)} if args.scenario == "sampled" else None

    def workload():
        for _ in range(args.loops):
            with tracer.start_as_current_span("root", attributes=attributes):
                with tracer.start_as_current_span("child", attributes=attributes):
                    pass

    profile = cProfile.Profile()
    try:
        profile.runcall(workload)
    finally:
        provider.shutdown()
    profile.dump_stats(str(destination / "profile.pstats"))
    with (destination / "summary.txt").open("w", encoding="utf-8") as stream:
        pstats.Stats(profile, stream=stream).strip_dirs().sort_stats("tottime").print_stats(40)
    paths = [
        "opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py",
        "opentelemetry-sdk/src/opentelemetry/sdk/trace/sampling.py",
        "opentelemetry-api/src/opentelemetry/trace/__init__.py",
        "opentelemetry-api/src/opentelemetry/trace/propagation/__init__.py",
        "opentelemetry-api/src/opentelemetry/attributes/__init__.py",
    ]
    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "scenario": args.scenario,
        "loops": args.loops,
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths},
        "scope": "Two nested spans per iteration, no configured exporter. Instrumented costs locate work; they are not CPU savings estimates.",
    }
    (destination / "run.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
