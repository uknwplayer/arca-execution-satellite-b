import json
import os
import tempfile
import unittest
from pathlib import Path

from executor.queue import load_request
from executor.run import execute_request


class QueueTests(unittest.TestCase):
    def write_request(self, root, name, payload):
        path = Path(root) / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def base_request(self, request_id="auto-001"):
        return {
            "schema": "arca.public-executor-request.v0.1",
            "profile": "smoke",
            "request_id": request_id,
            "public_only": True,
            "secrets_allowed": False,
        }

    def test_valid_queue_request(self):
        with tempfile.TemporaryDirectory() as root:
            request, metadata = load_request(
                self.write_request(root, "auto-001", self.base_request())
            )
            self.assertEqual(request.request_id, "auto-001")
            self.assertEqual(metadata["source"], "git-queue")

    def test_filename_must_match_request_id(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                load_request(
                    self.write_request(root, "different", self.base_request())
                )

    def test_secrets_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            payload = self.base_request()
            payload["secrets_allowed"] = True
            with self.assertRaises(ValueError):
                load_request(self.write_request(root, "auto-001", payload))

    def test_non_public_job_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            payload = self.base_request()
            payload["public_only"] = False
            with self.assertRaises(ValueError):
                load_request(self.write_request(root, "auto-001", payload))

    def test_extra_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            payload = self.base_request()
            payload["shell"] = "caller-controlled"
            with self.assertRaises(ValueError):
                load_request(self.write_request(root, "auto-001", payload))

    def test_mesh_executor_identity_is_bound_by_controlled_environment(self):
        previous = os.environ.get("ARCA_EXECUTOR_ID")
        try:
            os.environ["ARCA_EXECUTOR_ID"] = "github-satellite-linux"
            with tempfile.TemporaryDirectory() as root:
                request, metadata = load_request(
                    self.write_request(root, "identity-001", self.base_request("identity-001"))
                )
                payload = execute_request(
                    request,
                    output=Path(root) / "result.json",
                    request_metadata=metadata,
                )
            self.assertEqual(payload["executor_id"], "github-satellite-linux")
        finally:
            if previous is None:
                os.environ.pop("ARCA_EXECUTOR_ID", None)
            else:
                os.environ["ARCA_EXECUTOR_ID"] = previous


if __name__ == "__main__":
    unittest.main()
