# 0003. One setup per library repo writes the configuration

Status: accepted

`/setup-modelica-skills` runs once per library repo and writes `.modelica-skills/config.yml` plus a short section in `AGENTS.md`. It stores engine and how to reach it, Modelica and library versions, tracker, docs layout, the reference manifest path, unit conventions and the credibility classification type.

Not stored: tolerances. They depend on the component and the comparison and are declared in each issue. The setup may propose defaults per verification type, labelled as defaults.

Why: asking the engine on every task is noise; the repo-level choices are stable.
