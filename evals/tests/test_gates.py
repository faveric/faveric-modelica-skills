import shutil, tempfile, unittest
from pathlib import Path

from evals.adapters import omc_cli
from evals.mlgates import static, spec
from tools import lint_skills, mlrecord

ROOT = Path(__file__).resolve().parents[2]


class TestSkillsCompliance(unittest.TestCase):
    def test_skills_lint_passes(self):
        rc = lint_skills.main()
        self.assertEqual(rc, 0, "lint_skills failed")

    def test_skill_line_budget_and_invariants_are_linted(self):
        self.assertEqual(lint_skills.LINE_BUDGET, 120)
        self.assertIn("buildModel", lint_skills.INVARIANTS["verify-physics"])


class TestCredibilityRecord(unittest.TestCase):
    def test_template_record_loads_and_verifies(self):
        rec_path = ROOT / "templates" / "credibility-record.srmd.xml"
        self.assertTrue(rec_path.exists(), "Template record not found")
        ents = mlrecord.entries(mlrecord.load(rec_path))
        self.assertIn("org.mic-core.mic-core", ents)
        vals = mlrecord.values(ents, "org.mic-core.mic-core", mlrecord.VER_KEY)
        self.assertIn("has not been verified", vals)

    def test_cli_set_refuses_generated_keys(self):
        with tempfile.TemporaryDirectory() as d:
            w = Path(d)
            rec = w / "rec.srmd.xml"
            shutil.copy2(ROOT / "templates" / "credibility-record.srmd.xml", rec)
            rc = mlrecord.main(["set", str(rec), "x", "gate.G2", "pass"])
            self.assertEqual(rc, 2, "CLI set must refuse generated gate keys")


class TestStaticGates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        (self.work / "src").mkdir(parents=True)
        (self.work / "records").mkdir(parents=True)
        shutil.copy2(ROOT / "templates" / "credibility-record.srmd.xml", self.work / "records" / "credibility-record.srmd.xml")

    def tearDown(self):
        self.tmp.cleanup()

    def test_static_g1_and_g2_on_valid_model(self):
        mo = (
            "package TestPkg;\n"
            "  model MinimalValid;\n"
            '    Real v(unit="V", start=1.0, fixed=true) "Voltage";\n'
            '    Real i(unit="A") "Current";\n'
            '    parameter Real R(unit="Ohm") = 10 "Resistance";\n'
            "  equation\n"
            "    v = i * R;\n"
            "  end MinimalValid;\n"
            "end TestPkg;\n"
        )
        (self.work / "src" / "MinimalValid.mo").write_text(mo, encoding="utf-8")
        issue = (
            "---\n"
            "title: Minimal test issue\n"
            "level: L0\n"
            "model_files: [src/MinimalValid.mo]\n"
            "reference_state: ground_zero\n"
            "sources: []\n"
            "---\n"
            "# Spec\n"
        )
        (self.work / "ISSUE.md").write_text(issue, encoding="utf-8")
        s = spec.load_spec(self.work / "ISSUE.md")
        g1 = static.g1_syntax(self.work, s)
        self.assertEqual(g1[0], "skip", "Without engine G1 must report skip")
        g2 = static.g2_units(self.work, s)
        self.assertEqual(g2[0], "pass", "G2 must pass when all Real declarations carry unit")

    def test_static_g2_catches_missing_units(self):
        mo = (
            "package TestPkg;\n"
            "  model MinimalNoUnit;\n"
            '    Real v(start=1.0, fixed=true) "Voltage without unit";\n'
            "  equation\n"
            "    v = 1.0;\n"
            "  end MinimalNoUnit;\n"
            "end TestPkg;\n"
        )
        (self.work / "src" / "MinimalNoUnit.mo").write_text(mo, encoding="utf-8")
        issue = (
            "---\n"
            "title: Minimal test issue\n"
            "level: L0\n"
            "model_files: [src/MinimalNoUnit.mo]\n"
            "reference_state: ground_zero\n"
            "sources: []\n"
            "---\n"
        )
        (self.work / "ISSUE.md").write_text(issue, encoding="utf-8")
        s = spec.load_spec(self.work / "ISSUE.md")
        g2 = static.g2_units(self.work, s)
        self.assertEqual(g2[0], "fail", "G2 must catch missing unit attribute")


    def _gate(self, mo, bytes_=False):
        f = self.work / "src" / "M.mo"
        f.write_bytes(mo) if bytes_ else f.write_text(mo, encoding="utf-8")
        (self.work / "ISSUE.md").write_text(
            "---\ntitle: t\nlevel: L0\nmodel_files: [src/M.mo]\nreference_state: r\nsources: []\n---\n", encoding="utf-8")
        return spec.load_spec(self.work / "ISSUE.md")

    def test_non_ascii_and_invalid_bytes_do_not_crash(self):
        # 0xC3 0x81 is 'A' with acute in UTF-8; the lone 0x81 is undefined in cp1252 and invalid UTF-8
        mo = b"\xef\xbb\xbfmodel M\n  Real x(unit=\"K\") \"T \xc3\x81 \x81\";\nend M;\n"
        s = self._gate(mo, bytes_=True)
        self.assertEqual(static.g2_units(self.work, s)[0], "pass")
        self.assertEqual(static.g1_syntax(self.work, s)[0], "skip")

    def test_g2_commas_inside_array_literals_and_dimensions(self):
        mo = ('model M\n  parameter Real c[3](each unit="1") = {1.0e-3, 0, 105};\n'
              '  parameter Real m[2,3](each unit="1") = {{1,2,3},{4,5,6}};\nend M;\n')
        self.assertEqual(static.g2_units(self.work, self._gate(mo))[0], "pass")

    def test_g1_accepts_class_prefixes_and_short_definitions(self):
        mo = ("package M\n  pure function f\n    input Real x;\n    output Real y;\n  algorithm\n    y := x;\n  end f;\n"
              "  function g = f;\n  replaceable partial model B\n  end B;\nend M;\n")
        self.assertEqual(static.g1_syntax(self.work, self._gate(mo))[0], "skip")

    def test_g1_reports_which_side_is_missing(self):
        st, msg = static.g1_syntax(self.work, self._gate("model A\nend B;\n"))
        self.assertEqual(st, "fail")
        self.assertIn("class without 'end' line ['A']", msg)
        self.assertIn("'end' line without class ['B']", msg)

    def test_g5_assert_with_or_not_false_is_undecided_not_a_failure(self):
        for cond in ("T > 1 or T < 0", "not (T < 1)"):
            s = self._gate('model M\n  input Real T(unit="K");\nequation\n  assert(%s, "m");\nend M;\n' % cond)
            s["envelope"] = [{"var": "T", "min": 1, "max": None, "guard_min": 1, "guard_max": None, "guard_note": "n"}]
            st, msg = static.g5_guards(self.work, s)
            self.assertEqual(st, "skip", cond)
            self.assertIn("cannot decide from text", msg)

    def test_g5_still_fails_without_any_guard(self):
        s = self._gate('model M\n  input Real T(unit="K");\nequation\n  T = 1;\nend M;\n')
        s["envelope"] = [{"var": "T", "min": 1, "max": None, "guard_min": 1, "guard_max": None, "guard_note": "n"}]
        self.assertEqual(static.g5_guards(self.work, s)[0], "fail")

    def test_static_messages_carry_line_numbers(self):
        st, msg = static.g2_units(self.work, self._gate("model A\n  /* a\n  comment */\n  Real x;\nend A;\n"))
        self.assertEqual(st, "fail")
        self.assertIn("M.mo:4: x", msg)
        st, msg = static.g1_syntax(self.work, self._gate("model A\nequation\nend B;\n"))
        self.assertIn("A (line 1)", msg)


class TestEngineAdapter(unittest.TestCase):
    def test_omc_engine_detectable(self):
        info = omc_cli.engine_info()
        self.assertIsInstance(info, str)

    def test_omc_check_and_simulate_minimal_model(self):
        if not omc_cli.available():
            self.skipTest("omc not available in this environment")

        mo_content = (
            'model SyntheticDae "Domain-agnostic linear DAE test"\n'
            '  Real x(start=1.0, fixed=true);\n'
            '  parameter Real a = -1.0;\n'
            'equation\n'
            '  der(x) = a * x;\n'
            'end SyntheticDae;\n'
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "SyntheticDae.mo"
            p.write_text(mo_content, encoding="utf-8")

            chk = omc_cli.check_model([p], "SyntheticDae")
            self.assertTrue(chk.get("ok"), f"omc check_model failed: {chk}")
            self.assertEqual(chk.get("equations"), chk.get("variables"), "Equations must equal variables")

            sim = omc_cli.simulate([p], "SyntheticDae", stop_time=0.5, variables=["x"])
            self.assertTrue(sim.get("ok"), f"omc simulate failed: {sim}")
            self.assertIn("x", sim.get("series", {}))
            x_vals = sim["series"]["x"]
            self.assertGreater(len(x_vals), 1)
            # x(t) = exp(-t); at t=0.5, x ~ 0.606
            self.assertAlmostEqual(x_vals[-1], 0.606, delta=0.02)


if __name__ == "__main__":
    unittest.main()


class TestPluginPackaging(unittest.TestCase):
    def test_manifests_agree(self):
        import json
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
        self.assertEqual([p["name"] for p in market["plugins"]], [plugin["name"]])
        for d in plugin["skills"]:
            self.assertTrue((ROOT / d).is_dir(), d)

    def test_mcp_server_script_exists_and_is_not_named_mcp(self):
        import json
        cfg = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]["modelica"]
        script = cfg["args"][-1].replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT))
        self.assertTrue(Path(script).is_file(), script)
        self.assertFalse((ROOT / "mcp").exists(), "a top-level mcp/ would shadow the mcp package")


class TestNullBounds(unittest.TestCase):
    """A null envelope or validity bound means unbounded; it must not crash G5/G9 (ISSUE-002 case)."""

    def _spec(self, env, val):
        return {"level": "L0", "model_files": ["m.mo"], "envelope": env,
                "sources": [{"key": "k", "validity": val, "validity_verified": True, "locator": "x",
                             "transcription": "pending"}]}

    def test_g9_null_validity_bound_limits_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "m.mo").write_text("// cite: k\nmodel M end M;\n")
            (Path(d) / "refs.bib").write_text("@book{k, title={t}}\n")
            s = self._spec([{"var": "x", "min": 1, "max": 10}], [{"var": "x", "min": None, "max": None}])
            st, msg = static.g9_citations(d, s)
            self.assertNotIn("exceeds validity", msg)

    def test_g9_null_envelope_bound_exceeds_finite_validity(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "m.mo").write_text("// cite: k\nmodel M end M;\n")
            (Path(d) / "refs.bib").write_text("@book{k, title={t}}\n")
            s = self._spec([{"var": "x", "min": None, "max": 10}], [{"var": "x", "min": 0, "max": 20}])
            st, msg = static.g9_citations(d, s)
            self.assertEqual(st, "fail")
            self.assertIn("exceeds validity", msg)

    def test_g5_null_envelope_bound_does_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "m.mo").write_text("model M\n  Real x;\nequation\n  assert(x >= 0, \"x\");\n  x = 1;\nend M;\n")
            s = {"model_files": ["m.mo"], "envelope": [{"var": "x", "min": None, "max": None, "guard_min": 0, "guard_max": None, "guard_note": "open"}]}
            st, msg = static.g5_guards(d, s)
            self.assertIn(st, ("pass", "fail"))


try:
    import mcp.server.fastmcp  # noqa: F401
    HAVE_MCP = True
except ImportError:
    HAVE_MCP = False


@unittest.skipUnless(HAVE_MCP, "mcp package not installed")
class TestDymolaServer(unittest.TestCase):
    """Dymola is replaced by a fake interface; no Dymola install is needed (nor exercised)."""

    @classmethod
    def setUpClass(cls):
        import importlib.util, json, sys, types
        cfg = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]["dymola"]
        cls.script = Path(cfg["args"][-1].replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT)))
        spec_ = importlib.util.spec_from_file_location("dymola_mcp_under_test", cls.script)
        cls.mod = importlib.util.module_from_spec(spec_)
        spec_.loader.exec_module(cls.mod)

        class Fake:
            opened, closed = [], 0
            sim_result = (True, [1.5, 2.5])
            ok_translate = True

            def __init__(self, *a, **k): pass
            def openModel(self, p): Fake.opened.append(p); return "bad" not in p
            def cd(self, p): pass
            def ExecuteCommand(self, c): pass
            def translateModel(self, m): return Fake.ok_translate
            def getLastError(self): return "boom"
            def simulateExtendedModel(self, **kw): return Fake.sim_result
            def close(self): Fake.closed += 1

        cls.Fake = Fake
        pkg = types.ModuleType("dymola"); iface = types.ModuleType("dymola.dymola_interface")
        iface.DymolaInterface = Fake
        sys.modules.update({"dymola": pkg, "dymola.dymola_interface": iface})
        cls._sys = sys

    @classmethod
    def tearDownClass(cls):
        cls._sys.modules.pop("dymola", None); cls._sys.modules.pop("dymola.dymola_interface", None)

    def setUp(self):
        self.Fake.opened, self.Fake.closed = [], 0
        self.Fake.sim_result, self.Fake.ok_translate = (True, [1.5, 2.5]), True

    def test_server_script_exists(self):
        self.assertTrue(self.script.is_file(), self.script)

    def test_list_available_packages(self):
        with tempfile.TemporaryDirectory() as d:
            for rel in ("A/package.mo", "A/B/package.mo", ".git/package.mo"):
                p = Path(d) / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("package X end X;")
            self.assertEqual(self.mod.list_available_packages(d), ["A/B/package.mo", "A/package.mo"])
        with self.assertRaises(ValueError):
            self.mod.list_available_packages("/nonexistent-dir-xyz")

    def test_no_packages_is_an_error(self):
        with self.assertRaises(ValueError):
            self.mod.translate_model("M", packages=None)

    def test_translate_reports_bad_package_and_closes(self):
        r = self.mod.translate_model("M", packages=["/ok/package.mo", "/bad/package.mo"])
        self.assertFalse(r["success"])
        self.assertEqual(self.Fake.closed, 1)

    def test_translate_failure_carries_error(self):
        self.Fake.ok_translate = False
        r = self.mod.translate_model("M", packages=["/ok/package.mo"])
        self.assertEqual((r["success"], r["error"]), (False, "boom"))

    def test_run_simulation_maps_values_and_closes(self):
        r = self.mod.run_simulation("M", ["a", "b"], packages=["/ok/package.mo"])
        self.assertEqual(r, {"a": 1.5, "b": 2.5})
        self.assertEqual(self.Fake.closed, 1)

    def test_run_simulation_failure_flag_without_values_raises(self):
        self.Fake.sim_result = (False, [])
        with self.assertRaises(RuntimeError):
            self.mod.run_simulation("M", ["a"], packages=["/ok/package.mo"])
        self.assertEqual(self.Fake.closed, 1)

    def test_run_simulation_failure_flag_with_values_warns(self):
        self.Fake.sim_result = (False, [3.0])
        r = self.mod.run_simulation("M", ["a"], packages=["/ok/package.mo"])
        self.assertEqual(r["a"], 3.0)
        self.assertIn("boom", r["__warning__"])

    def test_run_simulation_validates_initials(self):
        with self.assertRaises(ValueError):
            self.mod.run_simulation("M", ["a"], packages=["/ok/package.mo"], initial_names=["p"], initial_values=[])
