import cProfile
import pstats

from opentelemetry.sdk.trace import TracerProvider, sampling

provider = TracerProvider(sampler=sampling.ParentBased(sampling.TraceIdRatioBased(0)), shutdown_on_exit=False)
tracer = provider.get_tracer("perf-investigation")


def workload():
    for _ in range(100_000):
        with tracer.start_as_current_span("root"):
            with tracer.start_as_current_span("child"):
                pass


profile = cProfile.Profile()
profile.runcall(workload)
profile.dump_stats(".agent/dropped-span-profile.pstats")
pstats.Stats(profile).strip_dirs().sort_stats("tottime").print_stats(24)
provider.shutdown()
