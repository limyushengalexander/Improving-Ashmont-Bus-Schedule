# November 6 status — 6.C57 Ashmont project

Course interim report due date **moved to Friday, November 13, 2026**. The team retains November 6 as the internal completion target.

| Planned November 6 deliverable | Status | Evidence |
|---|---|---|
| Formal mathematical formulation | Complete for finite one-minute grid | `docs/Scope_A_Mathematical_Formulation.md` |
| Initial Scope A optimization model | Completed, validated by exhaustive enumeration and independent MILP | `src/reference_enumeration.py`, `src/check_milp_with_scipy.py`, `results/` |
| Initial Julia/JuMP source code | Written, **not yet executed in Julia** | `src/run_scope_a.jl`, `Project.toml` |
| One-page interim report | Draft prepared and visually checked; not submitted | `Interim_Report_Draft_2026-11-06.docx`, `.pdf` |
| Model correctness and reproducibility | 12 Python tests pass; SciPy/HiGHS solver gap 0 | `results/test_log.txt`, `scipy_milp_crosscheck.json` |

**Study data:** 41 incoming opportunities, 37 eligible Route 215 departures, six adjustable, same historically reconciled October 15 archive. **Baseline:** mean post-allowance wait 13.5122 min, maximum 30 min. **Modeled optimum:** 12.4634 min, maximum 27 min, shifts `[-2,0,-2,-1,+2,0]` min; 7.76% improvement in average. No ridership weighting or MBTA operations approval.

**Before November 13 submission:** Three teammates should review the one-page text, verify the course's exact interim-report format and submission instructions, run the Julia script on a system with Julia, and compare its outcome against the solved independent MILP. If the Julia run cannot be completed before submission, retain the transparent status statement rather than claiming it ran.

**Nov 7-15 project stage:** Add a documented simple-feasible heuristic, model timing benchmarks and sensitivity analysis. Consider Scope B only after validation of date-specific historical observations, delay timestamps, and Quincy terminal vehicle availability.
