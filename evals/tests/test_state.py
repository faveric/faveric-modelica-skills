"""tools/mlstate.py: the stage of the work, derived from files (ADR-0019)."""
import json, shutil, tempfile, unittest
from pathlib import Path

from tools import mlissue, mlstate

ROOT = Path(__file__).resolve().parents[2]
HEADER = "---\nid: ISSUE-001\ntitle: t\nlevel: L0\nmodel_files: [src/M.mo]\nsources: []\n---\n# t\n"


def task(tid, boxes, blocked=(), question="Does y follow T?", issue="ISSUE-001"):
    b = "\n".join(f"- [{'x' if v else ' '}] check {i}" for i, v in enumerate(boxes))
    return (f"---\nid: {tid}\nissue: {issue}\ntype: AFK\nblocked_by: {list(blocked)}\n---\n# {tid}\n\n"
            f"## Physical question\n{question}\n\n## Done when\n{b}\n")


class StateCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        (self.d / ".modelica-skills").mkdir()
        (self.d / ".modelica-skills" / "config.yml").write_text("tracker: {kind: files, path: docs/tasks}\n", encoding="utf-8")
        (self.d / "docs" / "issues").mkdir(parents=True)
        (self.d / "docs" / "tasks").mkdir(parents=True)

    def issue(self, text=HEADER):
        (self.d / "docs" / "issues" / "ISSUE-001.md").write_text(text, encoding="utf-8")

    def task(self, name, *a, **k):
        (self.d / "docs" / "tasks" / name).write_text(task(*a, **k), encoding="utf-8")

    def stage(self):
        return mlstate.state(self.d)["issues"][0]


class TestStages(StateCase):
    def test_no_config_then_no_issue(self):
        (self.d / ".modelica-skills" / "config.yml").unlink()
        self.assertEqual(mlstate.state(self.d)["next"]["command"], "/setup-modelica-skills")
        (self.d / ".modelica-skills" / "config.yml").write_text("tracker: {kind: files}\n", encoding="utf-8")
        self.assertEqual(mlstate.state(self.d)["next"]["command"], "/interview-model")

    def test_bad_header_then_no_tasks(self):
        self.issue("no front matter here")
        self.assertEqual(self.stage()["stage"], "header")
        self.issue()
        s = self.stage()
        self.assertEqual((s["stage"], s["next"]), ("tasks", "/to-tasks"))

    def test_open_tasks_pick_the_first_unblocked_one(self):
        self.issue()
        self.task("001.md", "T-001", [True, True])
        self.task("002.md", "T-002", [True, False], blocked=["T-001"])
        self.task("003.md", "T-003", [False], blocked=["T-002"])
        s = self.stage()
        self.assertEqual((s["stage"], s["task"], s["open_tasks"], s["total_tasks"]), ("implement", "T-002", 2, 3))
        self.assertEqual(mlstate.state(self.d)["next"], {"command": "/implement", "issue": "ISSUE-001", "why": s["why"]})

    def test_missing_physical_question_is_a_blocker(self):
        self.issue()
        self.task("001.md", "T-001", [False], question="One sentence: what physical fact must this task establish?")
        self.assertTrue(any("physical question" in b for b in self.stage()["blockers"]))

    def test_cycle_means_no_task_can_start(self):
        self.issue()
        self.task("001.md", "T-001", [False], blocked=["T-002"])
        self.task("002.md", "T-002", [False], blocked=["T-001"])
        s = self.stage()
        self.assertIsNone(s["next"])
        self.assertIn("cycle", s["why"])

    def test_review_learn_approve_done(self):
        self.issue()
        self.task("001.md", "T-001", [True])
        self.assertEqual(self.stage()["next"], "/review-model")
        shutil.copy2(ROOT / "templates" / "conclusion.md", self.d / "docs" / "issues" / "ISSUE-001-conclusion.md")
        s = self.stage()
        self.assertEqual((s["stage"], s["next"]), ("learn", None))
        self.assertIn("learn-from-issue", s["why"])
        ev = self.d / ".modelica-skills" / "learned"
        (ev / "evidence").mkdir(parents=True)
        (ev / "evidence" / "ISSUE-001.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.stage()["stage"], "done")
        (ev / "entries").mkdir()
        (ev / "entries" / "L-ISSUE-001-1.json").write_text(json.dumps({"id": "L-ISSUE-001-1", "issue": "ISSUE-001", "status": "candidate"}), encoding="utf-8")
        s = self.stage()
        self.assertEqual((s["stage"], s["next"]), ("approve", "/approve-lessons"))
        (ev / "entries" / "L-ISSUE-001-1.json").write_text(json.dumps({"id": "L-ISSUE-001-1", "issue": "ISSUE-001", "status": "active"}), encoding="utf-8")
        self.assertEqual(self.stage()["stage"], "done")

    def test_other_tracker_is_reported_not_guessed(self):
        (self.d / ".modelica-skills" / "config.yml").write_text("tracker: {kind: github}\n", encoding="utf-8")
        self.issue()
        s = self.stage()
        self.assertEqual(s["stage"], "tracker")
        self.assertIn("github", s["why"])


class TestWarnings(StateCase):
    def test_stale_summary_block_warns_and_state_changes_nothing(self):
        self.issue(HEADER + f"\n{mlissue.BEGIN}\nold\n{mlissue.END}\n")
        before = (self.d / "docs" / "issues" / "ISSUE-001.md").read_text(encoding="utf-8")
        self.assertTrue(any("at-a-glance" in w for w in self.stage()["warnings"]))
        self.assertEqual((self.d / "docs" / "issues" / "ISSUE-001.md").read_text(encoding="utf-8"), before)

    def test_stale_record_is_listed(self):
        from evals import run_gates
        from evals.tests.test_workflow import make_project
        p = make_project(self.d / "proj")
        run_gates.execute(p, write=True)
        (p / "src" / "M.mo").write_text("// changed\n", encoding="utf-8")
        st = mlstate.state(p)
        self.assertTrue(any("G10" in w for w in st["record_warnings"]))

    def test_render_and_cli(self):
        self.issue()
        out = mlstate.render(mlstate.state(self.d))
        self.assertIn("stage tasks", out)
        self.assertIn("next: /to-tasks", out)
        self.assertEqual(mlstate.main(["--root", str(self.d), "--json"]), 0)


if __name__ == "__main__":
    unittest.main()
