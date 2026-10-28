import json
from pathlib import Path
import subprocess
import sys


def main():
    timer = sys.argv[1]
    for repeat in range(1, 4):
        modes = ("baseline", "candidate") if repeat % 2 else ("candidate", "baseline")
        for mode in modes:
            label = f"{mode}-{timer}-repeat-{repeat}"
            destination = Path(".agent") / f"{label}.json"
            command = [sys.executable, ".agent/run_benchmarks.py", mode,
                       "opentelemetry-sdk/benchmarks/trace/test_benchmark_dropped_spans.py",
                       "--benchmark-min-rounds=7", "--benchmark-min-time=0.02",
                       "--benchmark-max-time=0.3", "--benchmark-warmup=on",
                       "--benchmark-warmup-iterations=2000", f"--benchmark-json={destination}",
                       "--benchmark-columns=median,iqr", "-q"]
            if timer == "cpu":
                command.extend(["--benchmark-timer=time.process_time", "-k", "not context_set_value"])
            log = destination.with_suffix(".log")
            with log.open("w") as output:
                result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT)
            if result.returncode:
                print(log.read_text()[-5000:], flush=True)
                raise SystemExit(result.returncode)
            data = json.loads(destination.read_text())
            print(f"{label}: {len(data['benchmarks'])} cases, saved {destination}", flush=True)


if __name__ == "__main__":
    main()
