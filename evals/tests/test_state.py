"""tools/mlstate.py: the stage of the work, derived from files (ADR-0019)."""
import json, shutil, subprocess, tempfile, unittest
from pathlib import Path

from tools import mlissue, mlstate

ROOT = Path(__file__).resolve().parents[2]
HEADER = "---\nid: ISSUE-001\ntitle: t\nlevel: L0\nmodel_files: [src/M.mo]\nsources: []\n---\n# t\n"


def task(tid, boxes, blocked=(), question="Does y follow T?", issue="ISSUE-001", status=None):
    b = "\n".join(f"- [{'x' if v else ' '}] check {i}" for i, v in enumerate(boxes))
    st = f"status: {status}\n" if status else ""
    return (f"---\nid: {tid}\nissue: {issue}\ntype: AFK\n{st}blocked_by: {list(blocked)}\n---\n# {tid}\n\n"
            f"## Physical question\n{question}\n\n## Answer\n{'y follows T within 2%. credibility: partial.' if all(boxes) else ''}\n\n"
            f"## Done when\n{b}\n")


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
        (self.d / "docs" / "issues" / "00001 [ISSUE-001] - t.md").write_text(text, encoding="utf-8")

    def task(self, tid, *a, **k):
        name = f"{int(tid.split('-')[1]):05d} [{k.get('issue', 'ISSUE-001')}] [{tid}] - t.md"  # the number is the T-id's, so "#1" names T-001
        (self.d / "docs" / "tasks" / name).write_text(task(tid, *a, **k), encoding="utf-8")

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
        self.task("T-001", [True, True])
        self.task("T-002", [True, False], blocked=["#1"])
        self.task("T-003", [False], blocked=["#2"])
        s = self.stage()
        self.assertEqual((s["stage"], s["task"], s["open_tasks"], s["total_tasks"]), ("implement", "T-002", 2, 3))
        self.assertEqual(mlstate.state(self.d)["next"], {"command": "/implement", "issue": "ISSUE-001", "why": s["why"]})

    def test_missing_physical_question_is_a_blocker(self):
        self.issue()
        self.task("T-001", [False], question="One sentence: what physical fact must this task establish?")
        self.assertTrue(any("physical question" in b for b in self.stage()["blockers"]))

    def test_cycle_means_no_task_can_start(self):
        self.issue()
        self.task("T-001", [False], blocked=["#2"])
        self.task("T-002", [False], blocked=["#1"])
        s = self.stage()
        self.assertIsNone(s["next"])
        self.assertIn("cycle", s["why"])

    def test_review_learn_approve_done(self):
        self.issue()
        self.task("T-001", [True])
        self.assertEqual(self.stage()["next"], "/review-model")
        (self.d / "docs" / "issues" / "ISSUE-001-conclusion.md").write_text((ROOT / "templates" / "conclusion.md").read_text(encoding="utf-8").replace("**Outcome: met | missed**, measured <value> vs target <value>", "**Outcome: met**, error 4% vs target 10%"), encoding="utf-8")
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

    def test_missed_outcome_routes_to_the_failure_interview_before_the_learner(self):
        from tools import mllearn
        self.issue()
        self.task("T-001", [True])
        text = (ROOT / "templates" / "conclusion.md").read_text(encoding="utf-8").replace(
            "**Outcome: met | missed**, measured <value> vs target <value>", "**Outcome: missed**, error 30% vs target 10%")
        (self.d / "docs" / "issues" / "ISSUE-001-conclusion.md").write_text(text, encoding="utf-8")
        s = self.stage()
        self.assertEqual((s["stage"], s["next"]), ("failure", "/interview-failed-issue"))
        with self.assertRaises(ValueError) as c:
            mllearn.collect(self.d, "ISSUE-001")
        self.assertIn("interview-failed-issue", str(c.exception))
        (self.d / "docs" / "issues" / "ISSUE-001-failure.md").write_text("# f\n\n## Decision\nstop\n", encoding="utf-8")
        self.assertEqual(self.stage()["stage"], "learn")
        _, bundle = mllearn.collect(self.d, "ISSUE-001")
        self.assertIn("failure", {i["kind"] for i in bundle["items"]})
        self.assertEqual(len(mlstate.state(self.d)["issues"]), 1)  # the failure note is not an issue

    def test_other_tracker_is_reported_not_guessed(self):
        (self.d / ".modelica-skills" / "config.yml").write_text("tracker: {kind: github}\n", encoding="utf-8")
        self.issue()
        s = self.stage()
        self.assertEqual(s["stage"], "tracker")
        self.assertIn("github", s["why"])


class Helpers:
    def put(self, iid, extra=""):
        text = f"---\nid: {iid}\ntitle: t\nlevel: L0\nmodel_files: [src/M.mo]\nsources: []\n{extra}---\n# t\n"
        name = f"{int(iid.split('-')[1]):05d} [{iid}] - t.md"
        (self.d / "docs" / "issues" / name).write_text(text, encoding="utf-8")

    def issues(self):
        return {i["id"]: i for i in mlstate.state(self.d)["issues"]}


class TestTaskStatus(StateCase):
    def test_task_awaiting_approval_waits_for_the_person(self):
        self.issue()
        self.task("T-001", [False], status="awaiting-approval")
        s = self.stage()
        self.assertEqual((s["stage"], s["next"], s["awaiting_approval"]), ("approval", None, ["T-001"]))
        self.assertIn("approved", s["why"])
        self.assertIn("/implement", s["why"])
        self.task("T-001", [True])  # approved: the agent ticks the boxes and clears the status
        self.assertEqual(self.stage()["next"], "/review-model")

    def test_status_must_be_known(self):
        self.issue()
        self.task("T-001", [False], status="almost-done")
        self.assertTrue(any("almost-done" in w for w in self.stage()["warnings"]))


class TestBlockers(Helpers, StateCase):
    def test_a_task_waits_for_the_task_number_it_names_and_says_which(self):
        self.issue()
        self.task("T-001", [False])
        self.task("T-002", [False], blocked=["#1"])
        got = self.stage()
        self.assertEqual((got["next"], got["task"]), ("/implement", "T-001"))
        self.assertEqual(got["waiting"], ["T-002 waits for #1 (open)"])
        self.task("T-001", [True])
        got = self.stage()
        self.assertEqual((got["task"], got["waiting"]), ("T-002", []))

    def test_a_number_that_names_nothing_is_reported_not_guessed(self):
        self.issue()
        self.task("T-001", [False], blocked=["#9"])
        got = self.stage()
        self.assertEqual((got["stage"], got["next"]), ("implement", None))
        self.assertTrue(any("#9" in w and "unknown" in w for w in got["waiting"]))
        self.assertNotIn("cycle", got["why"])


class TestOverview(Helpers, StateCase):
    def test_each_issue_has_a_goal_an_opening_order_and_what_it_waits_for(self):
        self.put("ISSUE-001", "decision: pick the correlation\n")
        self.put("ISSUE-002", "decision: fix the base\n")
        self.task("T-001", [False], issue="ISSUE-001")
        self.task("T-002", [False], blocked=["#1"], issue="ISSUE-001")
        got = self.issues()
        self.assertEqual((got["ISSUE-001"]["goal"], got["ISSUE-001"]["opened"]), ("pick the correlation", 1))
        self.assertEqual((got["ISSUE-002"]["goal"], got["ISSUE-002"]["opened"]), ("fix the base", 2))
        out = mlstate.render(mlstate.state(self.d))
        self.assertIn("goal: fix the base", out)
        self.assertIn("waits: T-002 waits for #1", out)


class TestWarnings(StateCase):
    def test_stale_summary_block_warns_and_state_changes_nothing(self):
        self.issue(HEADER + f"\n{mlissue.BEGIN}\nold\n{mlissue.END}\n")
        before = (self.d / "docs" / "issues" / "00001 [ISSUE-001] - t.md").read_text(encoding="utf-8")
        self.assertTrue(any("at-a-glance" in w for w in self.stage()["warnings"]))
        self.assertEqual((self.d / "docs" / "issues" / "00001 [ISSUE-001] - t.md").read_text(encoding="utf-8"), before)

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
