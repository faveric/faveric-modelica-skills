# 0012. Reference state and media are declared per issue; gate G8 checks interfaces

Status: **proposed** (needs the author's confirmation)

No default media library. `setup-modelica-skills` records the libraries available; each issue declares the medium and reference state it uses. G8 checks that components joined at a fluid interface share a reference state or declare a conversion.

Why: a circuit can close every component balance and still be wrong if two components use different zeros of enthalpy and entropy. Component-level gates cannot see this.

Limit: G8 can tell that two components disagree; it cannot say which one is right. That remains a human decision.

Open questions for the author: which libraries are used day to day, and has a reference-state mismatch bitten before? Who chooses the medium on a hosted platform: the library or the end user?
