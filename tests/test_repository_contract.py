import json
import re
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTest(unittest.TestCase):
    def test_versions_match(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        plugin = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((ROOT / ".github/plugin/marketplace.json").read_text(encoding="utf-8"))
        cli_text = (ROOT / "src/isee/cli.py").read_text(encoding="utf-8")
        version = re.search(r'^VERSION = "([^"]+)"$', cli_text, re.MULTILINE)
        self.assertIsNotNone(version)
        expected = project["project"]["version"]
        self.assertEqual(plugin["version"], expected)
        self.assertEqual(marketplace["metadata"]["version"], expected)
        self.assertEqual(version.group(1), expected)

    def test_agent_skills_and_links(self) -> None:
        self.assertTrue((ROOT / ".github/agents/isee.agent.md").is_file())
        expected = {"isee-init", "isee-plan", "isee-execute", "isee-review"}
        actual = {path.parent.name for path in (ROOT / ".github/skills").glob("*/SKILL.md")}
        self.assertEqual(actual, expected)
        missing = []
        for path in [ROOT / "README.md", *ROOT.joinpath("docs").rglob("*.md")]:
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                local = target.split("#", 1)[0]
                if local and not (path.parent / local).resolve().exists():
                    missing.append(f"{path.relative_to(ROOT)}: {target}")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
