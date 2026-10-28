"""Run identical benchmark code against HEAD functions or working tree functions."""

import ast
import subprocess
import sys

import pytest

from opentelemetry import context, trace
from opentelemetry.sdk.trace import sampling
from opentelemetry.trace import propagation


def head_function(path, name, namespace, class_name=None):
    source = subprocess.check_output(["git", "show", f"HEAD:{path}"], text=True)
    tree = ast.parse(source)
    nodes = tree.body
    if class_name:
        nodes = next(node for node in nodes if isinstance(node, ast.ClassDef) and node.name == class_name).body
    node = next(node for node in nodes if isinstance(node, ast.FunctionDef) and node.name == name)
    isolated = ast.Module(body=[node], type_ignores=[])
    result = namespace.copy()
    exec(compile(isolated, path, "exec"), result)
    return result[name]


mode = sys.argv[1]
if mode in ("baseline", "decision-only"):
    namespace = vars(propagation).copy()
    namespace["get_value"] = context.get_value
    original = head_function("opentelemetry-api/src/opentelemetry/trace/propagation/__init__.py", "get_current_span", namespace)
    propagation.get_current_span = original
    trace.get_current_span = original
    sampling.get_current_span = original
if mode in ("baseline", "lookup-only"):
    sampling.Decision.is_recording = head_function(
        "opentelemetry-sdk/src/opentelemetry/sdk/trace/sampling.py", "is_recording", vars(sampling), "Decision"
    )
if mode not in ("baseline", "candidate", "lookup-only", "decision-only"):
    raise ValueError(mode)

raise SystemExit(pytest.main(sys.argv[2:]))
