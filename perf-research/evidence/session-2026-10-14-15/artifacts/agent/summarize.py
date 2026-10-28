import json
from pathlib import Path
import statistics


summary = {}
for timer in ("wall", "cpu"):
    runs = {}
    for mode in ("baseline", "candidate"):
        paths = sorted(Path(".agent").glob(f"{mode}-{timer}-repeat-*.json"))
        if len(paths) != 3 or any(path.stat().st_size == 0 for path in paths):
            break
        runs[mode] = [{row["name"]: row["stats"]["median"] for row in json.loads(path.read_text())["benchmarks"]}
                      for path in paths]
    if len(runs) != 2:
        continue
    summary[timer] = {}
    for name in runs["baseline"][0]:
        values = {mode: [run[name] for run in cases] for mode, cases in runs.items()}
        baseline = statistics.median(values["baseline"])
        candidate = statistics.median(values["candidate"])
        summary[timer][name] = {
            "baseline_ns": baseline * 1e9,
            "candidate_ns": candidate * 1e9,
            "reduction_percent": 100 * (1 - candidate / baseline),
            "per_run_ns": {mode: [value * 1e9 for value in samples] for mode, samples in values.items()},
        }

Path(".agent/performance-summary.json").write_text(json.dumps(summary, indent=2))
for timer, cases in summary.items():
    print(timer)
    for name, stats in cases.items():
        if "context_set_value" not in name:
            print(f"{name}: {stats['baseline_ns'] / 1000:.3f} -> {stats['candidate_ns'] / 1000:.3f} us; "
                  f"{stats['reduction_percent']:+.1f}%")
