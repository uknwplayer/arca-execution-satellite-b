from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .contract import ExecutionRequest


def run_investigative_task(task_class: str, task_input: dict) -> dict:
    encoded = json.dumps(task_input, sort_keys=True, separators=(",", ":")).encode()
    input_sha256 = hashlib.sha256(encoded).hexdigest()
    if task_class == "PUBLIC_SOURCE_NORMALIZATION":
        return {"exit_code": 0, "task_class": task_class, "input_sha256": input_sha256, "normalized_keys": sorted(task_input)}
    if task_class == "ABSTRACT_TRACE_EXTRACTION":
        observations = task_input.get("observations", [])
        if not isinstance(observations, list) or any(not isinstance(x, str) for x in observations):
            raise ValueError("observations must be a string array")
        return {"exit_code": 0, "task_class": task_class, "input_sha256": input_sha256, "abstract_traces": sorted(set(observations))}
    if task_class == "SOURCE_LOCATOR_VERIFICATION":
        locators = task_input.get("locators", [])
        if not isinstance(locators, list) or any(not isinstance(x, str) for x in locators):
            raise ValueError("locators must be a string array")
        structural = [{"locator_sha256": hashlib.sha256(x.encode()).hexdigest(), "https": x.startswith("https://")} for x in locators]
        return {"exit_code": 0, "task_class": task_class, "input_sha256": input_sha256, "structural_checks": structural}
    if task_class == "TYPOLOGY_MATCHING":
        signals = task_input.get("signals", [])
        indicators = task_input.get("typology_indicators", [])
        if not isinstance(signals, list) or not isinstance(indicators, list):
            raise ValueError("signals and typology_indicators must be arrays")
        matches = sorted(set(map(str, signals)) & set(map(str, indicators)))
        return {"exit_code": 0, "task_class": task_class, "input_sha256": input_sha256, "matched_indicator_ids": matches, "match_is_finding": False}
    raise ValueError(task_class)


def run_profile(profile: str, task_class: str | None = None, task_input: dict | None = None) -> dict:
    if profile == "smoke":
        return {"exit_code": 0, "checks": ["python-runtime", "filesystem-write"]}
    if profile == "investigative-public-v0.1":
        return run_investigative_task(task_class or "", task_input or {})
    if profile == "python-unit":
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            check=False,
            text=True,
            capture_output=True,
        )
        return {
            "exit_code": completed.returncode,
            "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
        }
    raise ValueError(profile)


def execute_request(
    request: ExecutionRequest,
    *,
    output: str,
    request_metadata: dict | None = None,
) -> dict:
    request.validate()
    started = datetime.now(timezone.utc)
    result = run_profile(request.profile, request.task_class, request.task_input)
    finished = datetime.now(timezone.utc)
    payload = {
        "schema": "arca.public-executor-result.v0.1",
        "executor_id": os.getenv("ARCA_EXECUTOR_ID", "github-public-satellite"),
        "request_id": request.request_id,
        "profile": request.profile,
        "task_class": request.task_class,
        "git_sha": os.getenv("GITHUB_SHA", "local"),
        "run_id": os.getenv("GITHUB_RUN_ID", "local"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "result": result,
    }
    if request_metadata is not None:
        payload["request"] = request_metadata
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["result_sha256"] = hashlib.sha256(encoded).hexdigest()
    Path(output).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--output", default="execution-result.json")
    args = parser.parse_args()

    request = ExecutionRequest(profile=args.profile, request_id=args.request_id)
    payload = execute_request(request, output=args.output)
    print(json.dumps({
        "ok": payload["result"]["exit_code"] == 0,
        "executor_id": payload["executor_id"],
        "request_id": payload["request_id"],
        "profile": payload["profile"],
        "result_sha256": payload["result_sha256"],
    }, sort_keys=True))
    return int(payload["result"]["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
