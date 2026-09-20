import json
import tempfile
import unittest
from pathlib import Path

from executor.contract import ExecutionRequest
from executor.queue import load_request
from executor.run import run_investigative_task


class InvestigativePublicTaskTests(unittest.TestCase):
    def test_v02_queue_contract_accepts_allowlisted_public_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"mission.child.json"
            path.write_text(json.dumps({
                "schema":"arca.public-investigative-executor-request.v0.2",
                "profile":"investigative-public-v0.1",
                "request_id":"mission.child",
                "public_only":True,
                "secrets_allowed":False,
                "task_class":"TYPOLOGY_MATCHING",
                "task_input":{"signals":["RF-1"],"typology_indicators":["RF-1","RF-2"]}
            }))
            request,_=load_request(path)
            self.assertEqual(request.task_class,"TYPOLOGY_MATCHING")

    def test_typology_match_is_explicitly_not_a_finding(self):
        out=run_investigative_task("TYPOLOGY_MATCHING",{"signals":["RF-1"],"typology_indicators":["RF-1"]})
        self.assertEqual(out["matched_indicator_ids"],["RF-1"])
        self.assertFalse(out["match_is_finding"])

    def test_non_investigative_profile_rejects_task_metadata(self):
        with self.assertRaises(ValueError):
            ExecutionRequest("smoke","x",task_class="TYPOLOGY_MATCHING").validate()


if __name__=="__main__":
    unittest.main()
