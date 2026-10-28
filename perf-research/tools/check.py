"""Check research links, ledger consistency, and immutable evidence hashes."""

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

RESEARCH = Path(__file__).resolve().parents[1]
ROOT = RESEARCH.parent


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    errors = []
    ledger = read_json(RESEARCH / "ledger.json")
    manifest_path = RESEARCH / ledger["evidence_manifest"]
    manifest = read_json(manifest_path)
    read_json(manifest_path.parent / "validation-observed.json")
    candidates = {item["id"]: item for item in ledger["candidates"]}
    studies = {item["id"]: item for item in ledger["studies"]}
    if len(candidates) != len(ledger["candidates"]):
        errors.append("Duplicate candidate ID")
    if len(studies) != len(ledger["studies"]):
        errors.append("Duplicate study ID")

    def require_file(path):
        if not path.is_file():
            errors.append(f"Missing file: {path.relative_to(ROOT)}")
            return False
        return True

    for candidate_id, item in candidates.items():
        require_file(RESEARCH / item["owner"] / "README.md")
        notes = RESEARCH / item["notes"]
        if require_file(notes):
            body = notes.read_text(encoding="utf-8")
            for label, value in (("ID", candidate_id), ("Status", item["status"])):
                if not re.search(rf"^{label}: {re.escape(value)}\s*$", body, re.MULTILINE):
                    errors.append(f"{candidate_id}: notes disagree with ledger {label}")
        if item["status"] not in ledger["status_definitions"]:
            errors.append(f"{candidate_id}: unknown status {item['status']}")
        for study_id in item["studies"]:
            if study_id not in studies or candidate_id not in studies[study_id]["participants"]:
                errors.append(f"{candidate_id}: inconsistent study {study_id}")
    for study_id, item in studies.items():
        for candidate_id in item["participants"]:
            if candidate_id not in candidates or study_id not in candidates[candidate_id]["studies"]:
                errors.append(f"{study_id}: inconsistent participant {candidate_id}")
        for artifact in item["artifacts"]:
            require_file(RESEARCH / ledger["artifact_root"] / artifact)

    for record in manifest["artifacts"] + manifest["working_tree_sources"]:
        path = RESEARCH / record["path"]
        if require_file(path) and digest(path) != record["sha256"]:
            errors.append(f"Archive hash mismatch: {record['path']}")

    link_count = 0
    documents = [path for path in RESEARCH.rglob("*.md") if ".runs" not in path.parts]
    for path in documents:
        # This corpus uses inline Markdown links; fenced examples are not links.
        body = re.sub(r"(?ms)^(```|~~~).*?^\1[^\n]*$", "", path.read_text(encoding="utf-8"))
        for target in re.findall(r"!?\[[^\]\n]*\]\(([^)\n]+)\)", body):
            target = target.strip().strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            link_count += 1
            destination = (path.parent / unquote(parsed.path)).resolve()
            if not destination.exists():
                errors.append(f"Broken link in {path.relative_to(RESEARCH)}: {target}")

    drift = [
        item["source"]
        for item in manifest["working_tree_sources"]
        if not (ROOT / item["source"]).is_file() or digest(ROOT / item["source"]) != item["sha256"]
    ]
    if drift:
        print("Current sources differ from the historical snapshot (allowed):")
        for source in drift:
            print(f"  {source}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(
        f"Checked {len(candidates)} candidates, {len(studies)} studies, "
        f"{len(documents)} Markdown files, {link_count} local links, "
        f"{len(manifest['artifacts'])} artifact hashes and "
        f"{len(manifest['working_tree_sources'])} snapshot hashes."
    )


if __name__ == "__main__":
    main()
