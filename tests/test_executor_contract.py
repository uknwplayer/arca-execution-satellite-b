import json
import os
import tempfile
import unittest
from unittest.mock import patch

from executor.contract import ExecutionRequest
from executor.run import execute_request, run_profile


class ContractTests(unittest.TestCase):
    def test_smoke_profile_is_allowed(self):
        ExecutionRequest("smoke", "req-001").validate()

    def test_arbitrary_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            ExecutionRequest("shell-anything", "req-002").validate()

    def test_request_id_is_bounded(self):
        with self.assertRaises(ValueError):
            ExecutionRequest("smoke", "bad request id").validate()

    def test_smoke_executes_without_shell(self):
        result = run_profile("smoke")
        self.assertEqual(result["exit_code"], 0)

    def test_executor_identity_comes_from_bounded_environment(self):
        with tempfile.TemporaryDirectory() as root:
            output = os.path.join(root, "result.json")
            with patch.dict(os.environ, {"ARCA_EXECUTOR_ID": "github-public-windows"}):
                execute_request(ExecutionRequest("smoke", "req-003"), output=output)
            with open(output, encoding="utf-8") as handle:
                result = json.load(handle)
            self.assertEqual(result["executor_id"], "github-public-windows")


if __name__ == "__main__":
    unittest.main()
