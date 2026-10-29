"""The issue-end learner (tools/mllearn.py, ADR-0018): evidence, validation, approval, library, ledger."""
import json, shutil, subprocess, tempfile, unittest
from pathlib import Path

from tools import mllearn

ROOT = Path(__file__).resolve().parents[2]
SKILL = ("---\nname: pump-start-checks\ndescription: Use when a pump model fails to initialise after a start-up transient.\n---\n"
         "1. Set the start value of the head from the nominal point.\n2. Rerun the check.\n")


def git(d, *a):
    subprocess.run(["git", "-C", str(d), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True)


class LearnerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name) / "acmelib"
        (self.d / "docs" / "issues").mkdir(parents=True)
        (self.d / "src").mkdir()
        git(self.d, "init", "-q")
        (self.d / "src" / "M.mo").write_text("model M\n  assert(x > 0, \"m\");\nend M;\n", encoding="utf-8")
        (self.d / "docs" / "issues" / "ISSUE-001.md").write_text(
            "---\nid: ISSUE-001\nlevel: L0\nmodel_files: [src/M.mo]\ntolerances:\n  G3_energy_balance_rel: 1.0e-9\n"
            "accepted_gaps:\n  - {gate: G5, owner: o, date: 2026-01-01, reason: guard is a function}\n---\n", encoding="utf-8")
        git(self.d, "add", "-A"); git(self.d, "commit", "-q", "-m", "[ISSUE-001][T-001] first model")
        (self.d / "src" / "M.mo").write_text("model M\nend M;\n", encoding="utf-8")
        p = self.d / "docs" / "issues" / "ISSUE-001.md"
        p.write_text(p.read_text(encoding="utf-8").replace("1.0e-9", "1.0e-6"), encoding="utf-8")
        git(self.d, "add", "-A"); git(self.d, "commit", "-q", "-m", "[ISSUE-001][T-002] relax")
        (self.d / ".modelica-skills").mkdir()

    def conclude(self):
        shutil.copy2(ROOT / "templates" / "conclusion.md", self.d / "docs" / "issues" / "ISSUE-001-conclusion.md")

    def bundle(self):
        self.conclude()
        return mllearn.collect(self.d, "ISSUE-001")[1]

    def propose(self, **kw):
        args = dict(issue="ISSUE-001", kind="note", target="implement", title="Start values", evidence=["E1"],
                    body="Give pumps a start value for the head taken from the nominal point.")
        args.update(kw)
        return mllearn.propose(self.d, args["issue"], args["kind"], args["target"], args["title"], args["evidence"], args["body"])


class TestEvidence(LearnerCase):
    def test_collect_needs_the_conclusion(self):
        with self.assertRaises(ValueError) as c:
            mllearn.collect(self.d, "ISSUE-001")
        self.assertIn("after the conclusion", str(c.exception))

    def test_bundle_has_commits_gaps_and_owner_flags(self):
        items = self.bundle()["items"]
        kinds = {i["kind"] for i in items}
        self.assertTrue({"conclusion", "commit", "accepted-gap", "flag"} <= kinds)
        refs = {i["ref"] for i in items if i["kind"] == "flag"}
        self.assertIn("assert-removed-or-rewritten", refs)
        self.assertIn("tolerance-loosened", refs)
        self.assertEqual(items[0]["id"], "E1")


class TestPropose(LearnerCase):
    def setUp(self):
        super().setUp()
        self.items = {i["id"]: i for i in self.bundle()["items"]}

    def refused(self, **kw):
        with self.assertRaises(ValueError) as c:
            self.propose(**kw)
        return str(c.exception)

    def test_valid_note_is_a_candidate_and_not_in_the_library(self):
        e = self.propose()
        self.assertEqual((e["id"], e["status"]), ("L-ISSUE-001-1", "candidate"))
        self.assertFalse((self.d / ".modelica-skills" / "learned" / "implement.md").exists())

    def test_flags_unknown_evidence_and_missing_bundle_are_refused(self):
        flag = next(i for i in self.items if i.startswith("F"))
        self.assertIn("owner flag", self.refused(evidence=[flag]))
        self.assertIn("not in the bundle", self.refused(evidence=["E99"]))
        self.assertIn("no evidence bundle", self.refused(issue="ISSUE-009"))

    def test_text_that_weakens_checks_is_refused(self):
        for body in ("Loosen the tolerance when the gate fails.", "Remove the assert if it blocks the run.",
                     "Ignore the gate failure for pumps.", "See https://example.org/tip", "Skip the G5 check."):
            self.assertIn("refused", self.refused(body=body), body)

    def test_limits_duplicates_and_targets(self):
        self.propose(); self.assertIn("duplicates", self.refused())
        self.propose(title="b", body="second"); self.propose(title="c", body="third")
        self.assertIn("limit 3", self.refused(title="d", body="fourth"))
        self.assertIn("base skill name", self.refused(target="nope", title="e", body="x"))
        self.assertIn("at most 400", self.refused(title="f", body="x " * 300))

    def test_skill_shape(self):
        self.assertIn("front matter", self.refused(kind="skill", target="pump-start-checks", body="no front matter"))
        self.assertIn("extra keys", self.refused(kind="skill", target="pump-start-checks", body=SKILL.replace("---\n1.", "allowed-tools: Bash\n---\n1.")))
        self.assertIn("trigger sentence", self.refused(kind="skill", target="pump-start-checks", body=SKILL.replace("Use when", "For")))
        self.assertIn("not a base skill", self.refused(kind="skill", target="implement", body=SKILL.replace("pump-start-checks", "implement")))
        self.assertEqual(self.propose(kind="skill", target="pump-start-checks", body=SKILL)["status"], "candidate")

    def test_proposal_must_not_name_the_library(self):
        (self.d / "acme").mkdir()
        (self.d / "acme" / "package.mo").write_text("within ;\npackage AcmeThermo\nend AcmeThermo;\n", encoding="utf-8")
        self.assertIn("must not name the library", self.refused(kind="proposal", body="In AcmeThermo set the start value."))
        self.assertIn("must not name the library", self.refused(kind="proposal", body="In acmelib set the start value."))
        self.assertEqual(self.propose(kind="proposal", body="Set the start value from the nominal point.")["kind"], "proposal")


class TestApproval(LearnerCase):
    def setUp(self):
        super().setUp()
        self.bundle()
        self.learned = self.d / ".modelica-skills" / "learned"

    def test_note_is_installed_only_on_approval_with_a_ledger(self):
        e = self.propose()
        got = mllearn.approve(self.d, e["id"], "Ada")
        self.assertEqual(got["status"], "active")
        text = (self.learned / "implement.md").read_text(encoding="utf-8")
        self.assertIn(f"[{e['id']}]", text)
        self.assertIn(e["id"], (self.learned / "index.md").read_text(encoding="utf-8"))
        actions = [json.loads(ln)["action"] for ln in (self.learned / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(actions, ["proposed", "approved"])
        self.assertEqual(mllearn.verify(self.d), [])

    def test_approval_needs_a_name_and_a_candidate(self):
        e = self.propose()
        with self.assertRaises(ValueError):
            mllearn.approve(self.d, e["id"], " ")
        mllearn.approve(self.d, e["id"], "Ada")
        with self.assertRaises(ValueError):
            mllearn.approve(self.d, e["id"], "Ada")

    def test_skill_goes_to_the_library_skills_dir_and_never_overwrites(self):
        e = self.propose(kind="skill", target="pump-start-checks", body=SKILL)
        mllearn.approve(self.d, e["id"], "Ada")
        self.assertEqual((self.d / ".claude" / "skills" / "pump-start-checks" / "SKILL.md").read_text(encoding="utf-8"), SKILL)
        self.assertEqual(mllearn.verify(self.d), [])
        with self.assertRaises(ValueError):
            self.propose(kind="skill", target="pump-start-checks", title="again", body=SKILL)

    def test_proposals_are_not_installed(self):
        e = self.propose(kind="proposal", body="Set the start value from the nominal point.")
        with self.assertRaises(ValueError) as c:
            mllearn.approve(self.d, e["id"], "Ada")
        self.assertIn("pull request", str(c.exception))

    def test_edit_then_reject_and_retire_never_delete(self):
        e = self.propose()
        self.assertIn("nominal", mllearn.edit(self.d, e["id"], "Use the nominal head as the start value.")["body"] or "nominal")
        mllearn.reject(self.d, e["id"], "Ada", "too vague")
        self.assertEqual(mllearn._load_entries(self.d)[e["id"]]["status"], "rejected")
        s = self.propose(kind="skill", target="pump-start-checks", title="s", body=SKILL)
        mllearn.approve(self.d, s["id"], "Ada")
        mllearn.retire(self.d, s["id"], "Ada", "obsolete")
        self.assertFalse((self.d / ".claude" / "skills" / "pump-start-checks").exists())
        self.assertTrue((self.learned / "archive" / "pump-start-checks" / "SKILL.md").exists())
        self.assertEqual(mllearn._load_entries(self.d)[s["id"]]["status"], "archived")
        self.assertEqual(mllearn.verify(self.d), [])

    def test_verify_finds_edits_after_approval(self):
        s = self.propose(kind="skill", target="pump-start-checks", body=SKILL)
        mllearn.approve(self.d, s["id"], "Ada")
        (self.d / ".claude" / "skills" / "pump-start-checks" / "SKILL.md").write_text(SKILL + "extra\n", encoding="utf-8")
        self.assertIn("edited after approval", " ".join(mllearn.verify(self.d)))
        n = self.propose(title="note", body="A note about starts.")
        mllearn.approve(self.d, n["id"], "Ada")
        (self.learned / "implement.md").write_text("", encoding="utf-8")
        self.assertIn("edited or removed", " ".join(mllearn.verify(self.d)))

    def test_cli(self):
        self.assertEqual(mllearn.main(["list", "--root", str(self.d)]), 0)
        self.assertEqual(mllearn.main(["approve", "L-NOPE-1", "--by", "x", "--root", str(self.d)]), 1)


if __name__ == "__main__":
    unittest.main()
