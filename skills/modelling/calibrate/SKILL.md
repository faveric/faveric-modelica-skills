---
name: calibrate
description: Fit model parameters to data without hiding structural errors in the parameters and without validating on the fitted data.
disable-model-invocation: true
---

Use the `interviewing` rules for the setup.

**Before starting** (stop if any fails): the structural checks pass; the data has a known range, uncertainty and origin (ask); the issue lists the free parameters with physical bounds and units.

1. **Split the data first**, by operating condition, not at random: fit set and held-out set. Record the split and hash both.
2. **Fit** inside the bounds. Report the result and the parameter values (with uncertainty if available).
3. **Structure test.** A parameter on a bound, a physically odd value, or a trend in the residuals means the model structure is wrong. Stop, say so, suggest `/interview-model`. Do not widen bounds.
4. **Compare on the held-out set only**, against the issue's tolerance.
5. **Record** with `credibility-record`: "validated" only for the range actually covered, otherwise "validated with limitations" naming the range. Store the data hashes and parameters.
