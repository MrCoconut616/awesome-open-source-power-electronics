import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_audit", ROOT / "scripts/build_audit.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CatalogueTests(unittest.TestCase):
    def setUp(self):
        self.inputs = [json.loads((ROOT / ("catalogue/" + p)).read_text()) for p in ["tools.json", "source-snapshot.json", "connectors.json"]]

    def test_preserves_all_legacy_rows(self):
        data = module.audit(*self.inputs)
        self.assertEqual(36, sum(t["legacy"] for t in data["tools"]))
        for tool in data["tools"]:
            if tool["legacy"]:
                self.assertIn("[" + tool["name"] + "]", (ROOT / "README.md").read_text())
        self.assertEqual([], data["duplicate_source_groups"])

    def test_rejects_duplicate_and_unprobed_source(self):
        bad = copy.deepcopy(self.inputs)
        bad[0]["tools"].append(bad[0]["tools"][0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            module.audit(*bad)
        self.inputs[0]["tools"][0]["links"].append("https://example.invalid/missing")
        with self.assertRaisesRegex(ValueError, "unprobed"):
            module.audit(*self.inputs)

    def test_unknown_is_not_abandoned_or_open_source(self):
        self.inputs[1]["repositories"] = [{**r, "committed_at": None, "license": "NOASSERTION", "archived": False} for r in self.inputs[1]["repositories"]]
        data = module.audit(*self.inputs)
        femm = next(t for t in data["tools"] if t["id"] == "femm")
        self.assertEqual("source_available", femm["licence_class"])
        self.assertEqual("unknown", femm["maintenance"]["status"])

    def test_deterministic_without_clock_or_network(self):
        a = module.audit(*self.inputs)
        b = module.audit(*self.inputs)
        self.assertEqual(module.render(a), module.render(b))


if __name__ == "__main__":
    unittest.main()
