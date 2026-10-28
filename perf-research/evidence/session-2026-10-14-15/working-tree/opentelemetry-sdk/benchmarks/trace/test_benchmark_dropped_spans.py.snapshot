# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Iterator, Sequence

import pytest

from opentelemetry import context as context_api
from opentelemetry.context import Context, create_key, set_value
from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.sdk.trace.sampling import Decision, Sampler, SamplingResult
from opentelemetry.trace import Link, NonRecordingSpan, SpanContext, SpanKind, TraceFlags
from opentelemetry.trace.propagation import get_current_span, set_span_in_context
from opentelemetry.trace.span import TraceState
from opentelemetry.util.types import Attributes

_SET_KEY = create_key("benchmark")
_SET_VALUE = "value"
_ATTRIBUTES = {"benchmark.key": "value"}
_UNSAMPLED_PARENT = NonRecordingSpan(
    SpanContext(
        trace_id=0x123456789ABCDEF0123456789ABCDEF0,
        span_id=0x123456789ABCDEF0,
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.DEFAULT),
    )
)
_REMOTE_UNSAMPLED_PARENT = NonRecordingSpan(
    SpanContext(
        trace_id=0x123456789ABCDEF0123456789ABCDEF0,
        span_id=0x123456789ABCDEF0,
        is_remote=True,
        trace_flags=TraceFlags(TraceFlags.DEFAULT),
    )
)
_SDK_RECORDING_PARENT = "sdk-recording-parent"


class _DropSampler(Sampler):
    def should_sample(
        self,
        parent_context: Context | None,
        trace_id: int,
        name: str,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: Sequence[Link] | None = None,
        trace_state: TraceState | None = None,
    ) -> SamplingResult:
        return SamplingResult(Decision.DROP)

    def get_description(self) -> str:
        return "BenchmarkDropSampler"


@pytest.fixture(name="active_context")
def _active_context() -> Iterator[Context]:
    """Keep a populated ambient context active for each benchmark case."""
    context = Context(
        {
            "benchmark.baggage": {"item": "value"},
            "benchmark.extra": "value",
        }
    )
    token = context_api.attach(context)
    try:
        yield context
    finally:
        context_api.detach(token)


@pytest.mark.parametrize(
    ("context_size", "replace"),
    [
        (0, False),
        (1, False),
        (1, True),
        (2, False),
        (2, True),
        (8, False),
        (8, True),
    ],
    ids=[
        "empty-insert",
        "one-insert",
        "one-replace",
        "two-insert",
        "two-replace",
        "eight-insert",
        "eight-replace",
    ],
)
def test_context_set_value(benchmark, context_size: int, replace: bool) -> None:
    values = {f"key-{index}": index for index in range(context_size)}
    key = "key-0" if replace else _SET_KEY
    context = Context(values)

    benchmark(set_value, key, _SET_VALUE, context)


@pytest.mark.parametrize(
    ("sampler", "parent_kind"),
    [
        (sampling.ALWAYS_OFF, "root"),
        (sampling.ALWAYS_OFF, "unsampled-parent"),
        (sampling.ALWAYS_OFF, "remote-unsampled-parent"),
        (sampling.ParentBased(sampling.TraceIdRatioBased(0)), "root"),
        (sampling.ParentBased(sampling.TraceIdRatioBased(0)), "unsampled-parent"),
        (sampling.ParentBased(sampling.TraceIdRatioBased(0)), "remote-unsampled-parent"),
        (_DropSampler(), "root"),
        (_DropSampler(), "unsampled-parent"),
        (_DropSampler(), "remote-unsampled-parent"),
        (sampling.ALWAYS_ON, "root"),
        (sampling.ALWAYS_ON, "unsampled-parent"),
        (sampling.ALWAYS_ON, "remote-unsampled-parent"),
        (sampling.ALWAYS_OFF, _SDK_RECORDING_PARENT),
        (sampling.ALWAYS_ON, _SDK_RECORDING_PARENT),
    ],
    ids=[
        "always-off-root",
        "always-off-child",
        "always-off-remote-child",
        "parentbased-ratio-zero-root",
        "parentbased-ratio-zero-child",
        "parentbased-ratio-zero-remote-child",
        "custom-drop-root",
        "custom-drop-child",
        "custom-drop-remote-child",
        "always-on-root",
        "always-on-child",
        "always-on-remote-child",
        "always-off-sdk-recording-parent",
        "always-on-sdk-recording-parent",
    ],
)
@pytest.mark.parametrize("lifecycle", ["start-span", "current-span"])
def test_span_lifecycle(
    benchmark,
    active_context: Context,
    sampler: Sampler,
    parent_kind: str,
    lifecycle: str,
) -> None:
    provider = TracerProvider(sampler=sampler, shutdown_on_exit=False)
    tracer = provider.get_tracer("dropped-span-benchmark")
    parent_provider = None
    parent_span = None
    parent_context = None
    if parent_kind == "unsampled-parent":
        parent_context = set_span_in_context(_UNSAMPLED_PARENT, active_context)
    elif parent_kind == "remote-unsampled-parent":
        parent_context = set_span_in_context(_REMOTE_UNSAMPLED_PARENT, active_context)
    elif parent_kind == _SDK_RECORDING_PARENT:
        parent_provider = TracerProvider(sampler=sampling.ALWAYS_ON, shutdown_on_exit=False)
        parent_span = parent_provider.get_tracer("dropped-span-benchmark-parent").start_span("parent")
        parent_context = set_span_in_context(parent_span, active_context)

    if lifecycle == "start-span":

        def run() -> None:
            span = tracer.start_span("benchmark", context=parent_context, attributes=_ATTRIBUTES)
            span.end()

    else:

        def run() -> None:
            with tracer.start_as_current_span("benchmark", context=parent_context, attributes=_ATTRIBUTES):
                pass

    try:
        benchmark(run)
    finally:
        if parent_span is not None:
            parent_span.end()
        if parent_provider is not None:
            parent_provider.shutdown()
        provider.shutdown()


@pytest.mark.parametrize(
    ("parent_kind", "access"),
    [
        ("empty", "explicit"),
        ("empty", "implicit"),
        ("nonrecording", "explicit"),
        ("nonrecording", "implicit"),
        ("sdk-recording", "explicit"),
        ("sdk-recording", "implicit"),
    ],
    ids=[
        "empty-explicit",
        "empty-implicit",
        "nonrecording-explicit",
        "nonrecording-implicit",
        "sdk-recording-explicit",
        "sdk-recording-implicit",
    ],
)
def test_get_current_span(benchmark, parent_kind: str, access: str) -> None:
    parent_provider = None
    parent_span = None
    if parent_kind == "empty":
        context = Context()
    elif parent_kind == "nonrecording":
        context = set_span_in_context(_UNSAMPLED_PARENT)
    else:
        parent_provider = TracerProvider(sampler=sampling.ALWAYS_ON, shutdown_on_exit=False)
        parent_span = parent_provider.get_tracer("get-current-span-benchmark").start_span("parent")
        context = set_span_in_context(parent_span)

    token = context_api.attach(context) if access == "implicit" else None
    try:
        if access == "explicit":
            benchmark(get_current_span, context)
        else:
            benchmark(get_current_span)
    finally:
        if token is not None:
            context_api.detach(token)
        if parent_span is not None:
            parent_span.end()
        if parent_provider is not None:
            parent_provider.shutdown()
