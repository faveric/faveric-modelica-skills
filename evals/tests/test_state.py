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
        self.task("001.md", "T-001", [True])
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


class TestTaskStatus(StateCase):
    def test_ready_for_agent_tasks_are_listed_and_blocked_ones_wait(self):
        self.issue()
        self.task("001.md", "T-001", [False], status="ready-for-agent")
        self.task("002.md", "T-002", [False], blocked=["T-001"], status="ready-for-agent")
        self.task("003.md", "T-003", [False])  # not marked: the person has not released it
        self.assertEqual(self.stage()["ready"], ["T-001"])

    def test_task_awaiting_approval_waits_for_the_person(self):
        self.issue()
        self.task("001.md", "T-001", [True], status="awaiting-approval")
        s = self.stage()
        self.assertEqual((s["stage"], s["next"], s["awaiting_approval"]), ("approval", None, ["T-001"]))
        self.assertIn("/implement approve", s["why"])
        self.task("001.md", "T-001", [True], status="done")  # approved: implement sets done
        self.assertEqual(self.stage()["next"], "/review-model")

    def test_done_and_cancelled_close_a_task_whatever_the_boxes_say(self):
        self.issue()
        self.task("001.md", "T-001", [False], status="done")
        self.task("002.md", "T-002", [False], status="cancelled")
        s = self.stage()
        self.assertEqual((s["stage"], s["next"]), ("review", "/review-model"))

    def test_reopened_task_is_open_again_even_with_ticked_boxes(self):
        self.issue()
        self.task("001.md", "T-001", [True], status="ready-for-agent")
        s = self.stage()
        self.assertEqual((s["stage"], s["ready"]), ("implement", ["T-001"]))

    def test_tasks_for_a_human_are_listed_apart_from_agent_tasks(self):
        self.issue()
        self.task("001.md", "T-001", [False], status="ready-for-human")
        s = self.stage()
        self.assertEqual((s["ready"], s["ready_human"]), ([], ["T-001"]))

    def test_status_must_be_known(self):
        self.issue()
        self.task("001.md", "T-001", [False], status="almost-done")
        self.assertTrue(any("almost-done" in w for w in self.stage()["warnings"]))


class TestBranches(StateCase):
    def put(self, iid, extra):
        text = f"---\nid: {iid}\ntitle: t\nlevel: L0\nmodel_files: [src/M.mo]\nsources: []\n{extra}---\n# t\n"
        (self.d / "docs" / "issues" / f"{iid}.md").write_text(text, encoding="utf-8")

    def issues(self):
        return {i["id"]: i for i in mlstate.state(self.d)["issues"]}

    def test_stack_runs_from_main_through_the_issues_each_branch_started_from(self):
        self.put("ISSUE-001", "branch: issue-001-corr\nbase: main\n")
        self.put("ISSUE-002", "branch: issue-002-fix\nbase: ISSUE-001\ndiscovered_from: ISSUE-001\n")
        got = self.issues()
        self.assertEqual(got["ISSUE-001"]["stack"], ["main", "issue-001-corr"])
        self.assertEqual(got["ISSUE-002"]["stack"], ["main", "issue-001-corr", "issue-002-fix"])

    def conclude(self, iid, outcome):
        concl = (ROOT / "templates" / "conclusion.md").read_text(encoding="utf-8").replace(
            "**Outcome: met | missed**, measured <value> vs target <value>", f"**Outcome: {outcome}**, error 4% vs target 10%")
        (self.d / "docs" / "issues" / f"{iid}-conclusion.md").write_text(concl, encoding="utf-8")

    def test_parent_is_paused_while_a_spin_off_is_open_and_resumes_when_it_is_met(self):
        self.put("ISSUE-001", "branch: issue-001-corr\nbase: main\n")
        self.put("ISSUE-002", "branch: issue-002-fix\nbase: ISSUE-001\ndiscovered_from: ISSUE-001\n")
        self.task("001.md", "T-001", [False], issue="ISSUE-001")
        self.task("002.md", "T-002", [False], issue="ISSUE-002")
        got = self.issues()
        self.assertEqual((got["ISSUE-001"]["stage"], got["ISSUE-001"]["next"]), ("paused", None))
        self.assertIn("ISSUE-002", got["ISSUE-001"]["why"])
        nxt = mlstate.state(self.d)["next"]
        self.assertEqual((nxt["command"], nxt["issue"]), ("/implement", "ISSUE-002"))  # the fix comes first, not the paused parent
        self.task("002.md", "T-002", [True], issue="ISSUE-002")
        self.conclude("ISSUE-002", "met")
        self.assertEqual(self.issues()["ISSUE-001"]["stage"], "implement")  # resumes on the corrected base

    def test_failed_spin_off_keeps_the_parent_paused_until_the_owner_decides(self):
        self.put("ISSUE-001", "branch: issue-001-corr\nbase: main\n")
        self.put("ISSUE-002", "branch: issue-002-fix\nbase: ISSUE-001\ndiscovered_from: ISSUE-001\n")
        self.task("001.md", "T-001", [False], issue="ISSUE-001")
        self.task("002.md", "T-002", [True], issue="ISSUE-002")
        self.conclude("ISSUE-002", "missed")
        got = self.issues()["ISSUE-001"]
        self.assertEqual(got["stage"], "paused")
        self.assertIn("missed", got["why"])
        self.assertIn("proceeds_without", got["why"])  # option (a); option (b) is cancelling the parent's open tasks
        self.put("ISSUE-001", "branch: issue-001-corr\nbase: main\nproceeds_without:\n"
                              "  - {issue: ISSUE-002, owner: me, reason: base fix not needed here}\n")
        self.assertEqual(self.issues()["ISSUE-001"]["stage"], "implement")


class TestCurrentBranch(StateCase):
    put, issues = TestBranches.put, TestBranches.issues

    def git(self, *a):
        subprocess.run(["git", "-C", str(self.d), *a], check=True, capture_output=True)

    def test_working_on_the_wrong_branch_is_a_warning(self):
        self.put("ISSUE-001", "branch: issue-001-corr\nbase: main\n")
        self.task("001.md", "T-001", [False])
        self.git("init", "-q", "-b", "main")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "x")
        self.assertTrue(any("main" in w and "issue-001-corr" in w for w in self.issues()["ISSUE-001"]["warnings"]))
        self.git("checkout", "-q", "-b", "issue-001-corr")
        self.assertEqual(self.issues()["ISSUE-001"]["warnings"], [])

    def test_no_git_repository_means_no_branch_warning(self):
        self.put("ISSUE-001", "branch: issue-001-corr\nbase: main\n")
        self.task("001.md", "T-001", [False])
        self.assertEqual(self.issues()["ISSUE-001"]["warnings"], [])


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
