"""tools/mlwork.py: the work area, stray files and script headers (ADR-0022)."""
import shutil, subprocess, tempfile, unittest
from pathlib import Path

from tools import mlstate, mlwork

HEADER = "# Purpose: x\n# Inputs: a\n# Outputs: b\n# Issue: ISSUE-001\n# Run: python3 x.py\n"


@unittest.skipUnless(shutil.which("git"), "git not available")
class WorkCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.d)], check=True)
        (self.d / ".modelica-skills").mkdir()
        (self.d / ".modelica-skills" / "config.yml").write_text("tracker: {kind: files, path: docs/tasks}\n", encoding="utf-8")

    def put(self, rel, text="x"):
        p = self.d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


class TestPaths(WorkCase):
    def test_path_creates_and_defaults(self):
        p = mlwork.path_for(self.d, "ISSUE-001", "T-002", "out")
        self.assertEqual(p, self.d / ".modelica-skills" / "work" / "ISSUE-001" / "T-002" / "out")
        self.assertTrue(p.is_dir())
        base = mlwork.path_for(self.d, "ISSUE-001", "T-002")
        self.assertEqual(base, p.parent)
        for sub in ("data", "reports", "scripts", "out"):
            self.assertTrue((base / sub).is_dir())

    def test_unknown_subfolder_refused(self):
        with self.assertRaises(ValueError):
            mlwork.path_for(self.d, "ISSUE-001", None, "tmp")

    def test_config_overrides_root(self):
        (self.d / ".modelica-skills" / "config.yml").write_text("work: {root: scratch, subdirs: [a]}\n", encoding="utf-8")
        self.assertEqual(mlwork.path_for(self.d, "ISSUE-001", None, "a"), self.d / "scratch" / "ISSUE-001" / "a")

    def test_manifest_lists_files_with_sizes(self):
        mlwork.path_for(self.d, "ISSUE-001", "T-001")
        self.put(".modelica-skills/work/ISSUE-001/T-001/data/a.csv", "12345")
        self.assertEqual(mlwork.manifest(self.d, "ISSUE-001"), [("T-001/data/a.csv", 5)])
        self.assertEqual(mlwork.manifest(self.d, "ISSUE-009"), [])


class TestCheck(WorkCase):
    def test_stray_file_reported_allowed_ones_not(self):
        self.put("notes.md")
        self.put("analysis_v2.py")
        self.put("docs/issues/ISSUE-001.md")
        self.put("records/r.srmd.xml")
        self.put("scripts/run.py", HEADER)
        self.put("Lib/package.mo")
        self.put("Lib/Examples/M.mo")
        self.put("Lib/Resources/data.txt")
        self.put("README.md")
        self.assertEqual(sorted(mlwork.check(self.d)["stray"]), ["analysis_v2.py", "notes.md"])

    def test_gitignored_work_area_is_not_stray(self):
        self.put(".gitignore", "**/.modelica-skills/work/\n")
        self.put(".modelica-skills/work/ISSUE-001/data/a.csv")
        self.assertEqual(mlwork.check(self.d)["stray"], [])

    def test_script_without_header(self):
        self.put("scripts/good.py", HEADER + "print(1)\n")
        self.put("scripts/bad.py", "# Purpose: x\nprint(1)\n")
        r = mlwork.check(self.d)["scripts_without_header"]
        self.assertEqual([f for f, _ in r], ["scripts/bad.py"])
        self.assertIn("run", r[0][1])

    def test_check_never_touches_files(self):
        self.put("notes.md")
        mlwork.check(self.d)
        self.assertTrue((self.d / "notes.md").exists())

    def test_not_a_git_repo(self):
        with tempfile.TemporaryDirectory() as t:
            r = mlwork.check(t)
            self.assertFalse(r["git"])
            self.assertEqual(r["stray"], [])


class TestStartsessionWarning(WorkCase):
    def test_state_warns_about_stray_and_missing_key(self):
        self.put("notes.md")
        w = mlstate.state(self.d)["work_warnings"]
        self.assertTrue(any("stray file: notes.md" in x for x in w))
        self.assertTrue(any("no `work:` key" in x for x in w))

    def test_no_config_no_work_warning(self):
        (self.d / ".modelica-skills" / "config.yml").unlink()
        self.put("notes.md")
        self.assertEqual(mlstate.state(self.d)["work_warnings"], [])


if __name__ == "__main__":
    unittest.main()
