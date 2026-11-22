# Current status — November 22, 2026

**Status reviewed November 22; computational evidence recorded November 19.** This working revision updates the package folder, status/guide/memo filenames, documentation links, inventory, and release checksums. The memo contents, model inputs, solver code, experiment results, source archives, and November 12 interim report retain their historical evidence. No new optimization or Julia execution is claimed by changing the release date.

| Requested work | Status | Evidence |
|---|---|---|
| Protect Scope A baseline | Completed | Immutable original archives, input hashes, fresh raw-GTFS rebuild and original-result matches |
| Review formulation and code | Completed within the stated model scope | Exact formulation review, applied source patch, changes diff, unit and independent evaluator checks |
| Run Julia/JuMP and compare | **Pending / no execution recorded** | The November 19 authoring environment lacked Julia and runtime retrieval failed; no later Julia run evidence has been added |
| Rerun independent calculations | Completed | Exhaustive enumeration plus fresh SciPy/HiGHS zero-gap result |
| Simple feasible heuristic | Completed | Prespecified single chronological pass; matches nominal optimum |
| Sensitivity and model experiments | Completed in Python | 38 declared cases: 32 optimal, six structurally infeasible; 31 independently enumerated |
| Figures and interpretation | Completed | Four figures, tables, row-level changes, 33 block-neighbor and 300 stop-time checks |
| Consolidated package | Completed | All eight uploaded archives, current interim report, complete working model, new experiment code and evidence |
| Scope B | Deferred | No validated scenario model or delay-based recommendation claimed |
| Final technical report/slides/video | Not produced in this step | This is a working verification memo and research package |

## What changed in the project's conclusions?

The nominal 7.76% improvement is reproduced. The simple heuristic achieves the same result, so do not claim an advantage over that heuristic. The nominal fixed timetable performs poorly under longer transfer allowances; report reoptimization separately from stress testing. Stricter vehicle assumptions can make the entire model infeasible. A +/-2-minute shift limit retains the nominal benefit.

## Remaining minimum verification before final implementation claims

Run the reviewed Julia source on a machine with a functioning Julia installation and compare actual outputs with the saved independent results. Preserve solver status, objective bound/gap, Julia/package versions, and the generated Manifest. No seven-archive re-upload is necessary: the sources are now included.

## Review agenda for the team

Understand how readiness determines a missed connection, why whole-trip movement affects another route's vehicle, why the simple heuristic ties the optimizer, why a fixed nominal schedule can fail a parameter stress test, and why infeasible buffer assumptions are not comparable performance cases. Operational values remain research assumptions, not MBTA-approved rules.
