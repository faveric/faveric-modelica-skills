"""Gate runner end to end on a minimal project, accepted gaps, kept engine results, the Dymola adapter
(against a fake DymolaInterface), issue and lesson helpers. No engine and no Dymola are needed."""
import contextlib, io, shutil, sys, tempfile, types, unittest
from pathlib import Path

from evals import run_gates
from evals.mlgates import accept, spec as specmod, static, summary
from tools import mlissue, mlrecord

ROOT = Path(__file__).resolve().parents[2]

MODEL = ('package P\n  model M "doc"\n    input Real T(unit="K") "T";\n    Real y(unit="1");\n'
         '  equation\n    assert(T >= 280 and T <= 400, "T range");\n    y = T / 300;\n  end M;\nend P;\n'
         '// reference-state: r\n')
ISSUE = """---
id: ISSUE-001
title: minimal
level: {level}
decision: compare two options
model_files: [src/M.mo]
reference_state: {{id: r}}
envelope:
  - {{var: T, unit: K, min: 280, max: 400, guard_min: {gmin}, guard_max: 400}}
tolerances: {{G3_energy_balance_rel: 1.0e-9}}
sources: []
{gaps}verification:
  gates: [G1, G2, G3, G5]
  check_models: [P.M]
  simulations:
    - {{model: P.M, gate: G3, var: y, stop_time: 1.0, max_abs: 2.0}}
---
# minimal
"""


def make_project(d, level="L0", gmin=280, gaps=""):
    d = Path(d)
    (d / "src").mkdir(parents=True)
    (d / "records").mkdir()
    (d / "src" / "M.mo").write_text(MODEL, encoding="utf-8")
    (d / "ISSUE.md").write_text(ISSUE.format(level=level, gmin=gmin, gaps=gaps), encoding="utf-8")
    shutil.copy2(ROOT / "templates" / "credibility-record.srmd.xml", d / "records" / "credibility-record.srmd.xml")
    return d


def cli(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = run_gates.main(list(args))
    return rc, out.getvalue()


class TestRunGatesSmoke(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = make_project(Path(self.tmp.name) / "p")

    def tearDown(self):
        self.tmp.cleanup()

    def test_static_run_writes_record_and_summarises(self):
        rc, out = cli(str(self.d), "--write", "--question", "does y follow T?")
        self.assertEqual(rc, 0, out)
        self.assertIn("Physical question: does y follow T?", out)
        self.assertIn("SKIPPED", out)
        self.assertIn("PASSED", out)
        rc, out = cli(str(self.d))
        self.assertEqual(rc, 0, out)

    def test_raw_output_lists_every_gate(self):
        rc, out = cli(str(self.d), "--write", "--raw")
        self.assertRegex(out, r"G3\s+SKIP")
        self.assertRegex(out, r"RECORD\s+PASS")

    def test_non_utf8_issue_file_does_not_crash(self):
        p = self.d / "ISSUE.md"
        p.write_bytes(p.read_bytes().replace(b"minimal", "mínimo à".encode("utf-8"), 1))
        self.assertEqual(cli(str(self.d), "--write")[0], 0)


class TestKeptEngineResult(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = make_project(Path(self.tmp.name) / "p")
        cli(str(self.d), "--write")
        self.rec = self.d / "records" / "credibility-record.srmd.xml"
        ents = mlrecord.entries(mlrecord.load(self.rec))
        self.ext = mlrecord.ext_type(ents)
        self.digest = mlrecord.combined_digest(ents, self.ext, self.d)
        mlrecord.set_entry(self.rec, self.ext, "gate.G3", f"pass; engine=Dymola test; date=2026-01-01; hash={self.digest}")

    def tearDown(self):
        self.tmp.cleanup()

    def test_stored_pass_is_not_an_error_nor_overwritten_without_an_engine(self):
        rc, out = cli(str(self.d), "--raw")
        self.assertRegex(out, r"RECORD\s+PASS.*stored results kept")
        self.assertEqual(rc, 0)
        rc, out = cli(str(self.d), "--write")
        self.assertIn("record keeps its earlier pass", out)
        ents = mlrecord.entries(mlrecord.load(self.rec))
        self.assertTrue(mlrecord.values(ents, self.ext, "gate.G3")[0].startswith("pass; engine=Dymola test"))

    def test_changed_file_voids_the_stored_result(self):
        (self.d / "src" / "M.mo").write_text(MODEL + "// edit\n", encoding="utf-8")
        rc, out = cli(str(self.d), "--raw")
        self.assertRegex(out, r"G10\s+FAIL")
        cli(str(self.d), "--write")
        ents = mlrecord.entries(mlrecord.load(self.rec))
        self.assertTrue(mlrecord.values(ents, self.ext, "gate.G3")[0].startswith("skip"))


class TestAcceptedGaps(unittest.TestCase):
    GAP = "accepted_gaps:\n  - {gate: G5, owner: owner-a, date: 2026-01-02, reason: guard is a function call}\n"

    def project(self, **kw):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        return make_project(Path(self.tmp.name) / "p", **kw)

    def test_failing_gate_blocks_until_accepted(self):
        d = self.project(gmin=270)  # assert uses 280, the issue says 270: G5 fails
        rc, out = cli(str(d), "--write")
        self.assertEqual(rc, 1)
        self.assertIn("FAILED", out)
        d2 = Path(self.tmp.name) / "q"
        make_project(d2, gmin=270, gaps=self.GAP)
        rc, out = cli(str(d2), "--write", "--raw")
        self.assertEqual(rc, 0, out)
        self.assertRegex(out, r"G5\s+FAIL.*\[accepted gap\]")
        rc, out = cli(str(d2))
        self.assertIn("NEEDS A HUMAN DECISION", out)
        self.assertIn("owner-a", out)
        rec = d2 / "records" / "credibility-record.srmd.xml"
        ents = mlrecord.entries(mlrecord.load(rec))
        ext = mlrecord.ext_type(ents)
        self.assertEqual(mlrecord.values(ents, ext, "acceptance"), ["accepted with skipped gates: G5"])
        self.assertTrue(mlrecord.values(ents, ext, "accepted-gap")[0].startswith("G5|owner-a|2026-01-02|"))

    def test_gap_requires_owner_reason_and_l0(self):
        gaps, problems = accept.parse({"level": "L1", "accepted_gaps": [{"gate": "G5", "owner": "", "reason": "x"}, {"gate": "G10", "owner": "o", "reason": "r"}]})
        text = "; ".join(problems)
        self.assertIn("'owner' is required", text)
        self.assertIn("G10", text)
        self.assertIn("require level L0", text)
        d = self.project(level="L1", gaps=self.GAP)
        self.assertEqual(cli(str(d), "--write")[0], 1)

    def test_record_cannot_claim_verified_with_accepted_gaps(self):
        d = self.project(gmin=270, gaps=self.GAP)
        cli(str(d), "--write")
        rec = d / "records" / "credibility-record.srmd.xml"
        mic = "org.mic-core.mic-core"
        mlrecord.set_entry(rec, mic, mlrecord.VER_KEY, mlrecord.VERIFIED)
        msgs = " ".join(m for _, m in mlrecord.check(rec, d))
        self.assertIn("accepted gaps", msgs)


class TestRecordMessages(unittest.TestCase):
    def test_partial_is_not_a_status_and_the_message_says_where_free_text_goes(self):
        with tempfile.TemporaryDirectory() as t:
            d = make_project(Path(t) / "p")
            cli(str(d), "--write")
            rec = d / "records" / "credibility-record.srmd.xml"
            ents = mlrecord.entries(mlrecord.load(rec))
            ext = mlrecord.ext_type(ents)
            mlrecord.set_entry(rec, ext, "gate.G3", "partial: two of three cases pass, third needs the engine")
            msg = " ".join(m for _, m in mlrecord.check(rec, d))
            self.assertIn("note.<key>", msg)
            mlrecord.set_entry(rec, ext, "gate.G3", "open")
            mlrecord.set_entry(rec, ext, "note.G3", "two of three cases pass, third needs the engine " * 5)
            self.assertNotIn("unknown", " ".join(m for _, m in mlrecord.check(rec, d)))


class TestSummary(unittest.TestCase):
    def test_categories_and_causes(self):
        res = {"G1": ("pass", "ok"), "G2": ("fail", "Real without unit: M.mo:4: x. more text"), "G3": ("skip", "needs an engine"),
               "G9": ("open", "locator TO-VERIFY"), "G5": ("fail", "no guard")}
        out = summary.render(res, {"G5": {"owner": "o", "reason": "r", "date": ""}}, {"G3": "pass; engine=E; date=d; hash=h"}, "q?")
        self.assertTrue(out.startswith("Physical question: q?"))
        self.assertIn("FAILED (1):\n  - G2: Real without unit", out)
        self.assertIn("G5 accepted without passing (raw result: fail)", out)
        self.assertIn("G9 open", out)
        self.assertIn("record keeps its earlier pass", out)
        self.assertIn("PASSED (1): G1", out)


class FakeDymola:
    """Stands in for dymola.dymola_interface.DymolaInterface."""
    translate_ok = True
    traj = {"y": [0.5, 1.0, 1.4]}
    sim_ok = True
    with_traj = True

    def __init__(self, *a, **k): pass
    def openModel(self, p): return True
    def cd(self, p): pass
    def ExecuteCommand(self, c): pass
    def DymolaVersion(self): return "2026x-fake"
    def translateModel(self, m): return FakeDymola.translate_ok
    def getLastError(self): return "translation error: boom"
    def simulateExtendedModel(self, **kw): return (FakeDymola.sim_ok, [t[-1] for t in (FakeDymola.traj[n] for n in kw["finalNames"])])
    def readTrajectorySize(self, f):
        if not FakeDymola.with_traj: raise RuntimeError("no result file")
        return 3
    def readTrajectory(self, f, names, rows): return [FakeDymola.traj[n] for n in names]
    def close(self): pass


class TestDymolaAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pkg, iface = types.ModuleType("dymola"), types.ModuleType("dymola.dymola_interface")
        iface.DymolaInterface = FakeDymola
        sys.modules.update({"dymola": pkg, "dymola.dymola_interface": iface})

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop("dymola", None); sys.modules.pop("dymola.dymola_interface", None)

    def setUp(self):
        FakeDymola.translate_ok, FakeDymola.sim_ok, FakeDymola.with_traj = True, True, True
        FakeDymola.traj = {"y": [0.5, 1.0, 1.4]}
        self.tmp = tempfile.TemporaryDirectory()
        self.d = make_project(Path(self.tmp.name) / "p")
        cfg = self.d / ".modelica-skills"
        cfg.mkdir()
        (cfg / "config.yml").write_text("engine:\n  mode: mcp\n  backend: dymola\n  dymola:\n    packages: [/lib/package.mo]\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def gates(self, **kw):
        return run_gates.execute(self.d, engine="dymola", **kw)

    def test_pass_and_record_names_the_engine(self):
        res = self.gates(write=True)
        self.assertEqual(res["G1"][0], "pass", res["G1"])
        self.assertEqual(res["G3"][0], "pass", res["G3"])
        self.assertEqual(res["G4"][0], "skip")
        self.assertEqual(res["G2"][0], "pass")
        rec = self.d / "records" / "credibility-record.srmd.xml"
        ents = mlrecord.entries(mlrecord.load(rec))
        v = mlrecord.values(ents, mlrecord.ext_type(ents), "gate.G3")[0]
        self.assertIn("engine=Dymola 2026x-fake (via dymola_mcp)", v)
        self.assertEqual(res["RECORD"][0], "pass", res["RECORD"])

    def test_auto_engine_reads_the_config(self):
        self.assertEqual(run_gates.execute(self.d, engine="auto")["G3"][0], "pass")

    def test_bound_violation_fails(self):
        FakeDymola.traj = {"y": [0.5, 1.0, 2.5]}
        self.assertEqual(self.gates()["G3"][0], "fail")

    def test_translation_failure_fails_g1(self):
        FakeDymola.translate_ok = False
        st, msg = self.gates()["G1"]
        self.assertEqual(st, "fail")
        self.assertIn("boom", msg)

    def test_missing_trajectory_is_skip_never_pass(self):
        FakeDymola.with_traj = False
        st, msg = self.gates()["G3"]
        self.assertEqual(st, "skip")
        self.assertIn("trajectory not available", msg)

    def test_unavailable_interface_skips_with_the_reason(self):
        saved = sys.modules.pop("dymola.dymola_interface")
        try:
            sys.modules["dymola.dymola_interface"] = None  # makes the import fail
            res = self.gates()
        finally:
            sys.modules["dymola.dymola_interface"] = saved
        self.assertEqual(res["G3"][0], "skip")
        self.assertIn("Dymola not usable", res["G3"][1])


class TestIssueHelpers(unittest.TestCase):
    def test_title_label_and_summary_block(self):
        self.assertEqual(mlissue.task_title("ISSUE-001", "T-005", " Pressure drop "), "[ISSUE-001][T-005] Pressure drop")
        self.assertEqual(mlissue.label("ISSUE-001"), "issue-001")
        with tempfile.TemporaryDirectory() as t:
            d = make_project(Path(t) / "p", gaps=TestAcceptedGaps.GAP)
            text = (d / "ISSUE.md").read_text(encoding="utf-8")
            (d / "ISSUE.md").write_text(text + f"\n{mlissue.BEGIN}\n{mlissue.END}\n", encoding="utf-8")
            self.assertEqual(mlissue.main(["summary", str(d / "ISSUE.md"), "--check"]), 1)
            self.assertEqual(mlissue.main(["summary", str(d / "ISSUE.md"), "--write"]), 0)
            self.assertEqual(mlissue.main(["summary", str(d / "ISSUE.md"), "--check"]), 0)
            body = (d / "ISSUE.md").read_text(encoding="utf-8")
            self.assertIn("| T | K | 280 | 400 | 280 | 400 |", body)
            self.assertIn("| G3 | energy_balance_rel = 1e-09 | – |", body)
            self.assertIn("Accepted gaps", body)
            specmod.load_spec(d / "ISSUE.md")  # the header still parses

    def test_can_close_needs_the_conclusion(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(mlissue.can_close("ISSUE-001", t))
            shutil.copy2(ROOT / "templates" / "conclusion.md", Path(t) / "ISSUE-001-conclusion.md")
            self.assertEqual(mlissue.can_close("ISSUE-001", t), [])


if __name__ == "__main__":
    unittest.main()
