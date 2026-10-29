# 0001. Unit of work: component, then system, then calibration

Status: accepted

The skills cover three levels in dependency order. A component declares its envelope and gate results; a system consumes component records and fails if a component is used outside its envelope or has a stale record; calibration only runs on a model whose structural gates pass.

Why: a calibration can hide a structural error by bending parameters. Ordering the levels makes the envelope the interface between them.

Consequence: every component record carries an envelope, and system issues list component record versions.
