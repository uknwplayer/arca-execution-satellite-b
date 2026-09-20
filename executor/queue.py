from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .contract import ExecutionRequest
from .run import execute_request


REQUEST_SCHEMA_V1 = "arca.public-executor-request.v0.1"
REQUEST_SCHEMA_V2 = "arca.public-investigative-executor-request.v0.2"
REQUEST_KEYS_V1 = frozenset({
    "schema",
    "profile",
    "request_id",
    "public_only",
    "secrets_allowed",
})
REQUEST_KEYS_V2 = REQUEST_KEYS_V1 | frozenset({"task_class", "task_input"})


def load_request(path: Path) -> tuple[ExecutionRequest, dict]:
    raw = path.read_bytes()
    data = json.loads(raw)

    if not isinstance(data, dict):
        raise ValueError("request must be a JSON object")
    schema = data.get("schema")
    if schema not in {REQUEST_SCHEMA_V1, REQUEST_SCHEMA_V2}:
        raise ValueError("unsupported request schema")
    expected_keys = REQUEST_KEYS_V2 if schema == REQUEST_SCHEMA_V2 else REQUEST_KEYS_V1
    if set(data) != expected_keys:
        raise ValueError("request keys do not match the declared contract")
    if data["public_only"] is not True:
        raise ValueError("queued public jobs must declare public_only=true")
    if data["secrets_allowed"] is not False:
        raise ValueError("queued public jobs must declare secrets_allowed=false")

    request = ExecutionRequest(
        profile=data["profile"],
        request_id=data["request_id"],
        task_class=data.get("task_class"),
        task_input=data.get("task_input", {}),
    )
    request.validate()

    if path.stem != request.request_id:
        raise ValueError("request_id must match the request filename")

    metadata = {
        "source": "git-queue",
        "path": path.as_posix(),
        "request_sha256": hashlib.sha256(raw).hexdigest(),
    }
    return request, metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-file", required=True)
    parser.add_argument("--output", default="execution-result.json")
    args = parser.parse_args()

    request, metadata = load_request(Path(args.request_file))
    payload = execute_request(
        request,
        output=args.output,
        request_metadata=metadata,
    )
    print(json.dumps({
        "ok": payload["result"]["exit_code"] == 0,
        "executor_id": payload["executor_id"],
        "request_id": payload["request_id"],
        "profile": payload["profile"],
        "task_class": payload.get("task_class"),
        "request_sha256": metadata["request_sha256"],
        "result_sha256": payload["result_sha256"],
    }, sort_keys=True))
    return int(payload["result"]["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
