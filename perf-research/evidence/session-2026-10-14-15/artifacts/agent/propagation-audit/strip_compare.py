"""Follow-up: validate the fixed record with a native allowlist strip."""
import hashlib
import json
import sys
from pathlib import Path

import parser_compare as base

source = base.SOURCES["translate"].replace("value.translate(_DELETE_HEX)", "value.strip(_HEX_DASH)")
namespace = vars(base.audit.tc).copy()
namespace["_HEX_DASH"] = base.HEX + "-"
exec(compile(source, "<traceparent-strip>", "exec"), namespace)
base.CANDIDATES["strip"] = namespace["extract"]
base.SOURCES["strip"] = source
if __name__ == "__main__":
    output_path = ".agent/propagation-audit/paired-strip-comparison.json"
    sys.argv = [
        __file__, "--mode", "optimized-regex", "--mode", "strip",
        "--seconds", "0.9", "--repeats", "9", "--output", output_path,
    ]
    base.main()
    output = json.loads(Path(output_path).read_text(encoding="utf-8"))
    output["metadata"]["followup_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    Path(output_path).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
