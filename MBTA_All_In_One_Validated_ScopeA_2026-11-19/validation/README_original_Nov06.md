# 6.C57 Ashmont Scope A — model and interim report (November 6, 2026)

**Team:** Alex Lim · Yun Ji Seo · Luran Wang  
**Revised interim report due date:** Friday, November 13, 2026 (team will aim to finish internally November 6).  
**Main task:** deterministic Route 215 timetable coordination at Ashmont; Scope B delay validation is deferred.

## What this package delivers

- `docs/Scope_A_Mathematical_Formulation.md` — rigorous finite-grid MILP and proof of earliest departure treatment, data provenance, and limitations.
- `src/run_scope_a.jl` — **initial Julia/JuMP/HiGHS model**, including complete-trip output shifts and independent baseline/feasibility checks. **Not executed here; Julia was not installed**.
- `src/reference_enumeration.py` — executed Python independent exhaustive check, obtaining the exact finite-grid model optimum and feasible-grid count.
- `src/check_milp_with_scipy.py` — an independently implemented SciPy/HiGHS MILP, solved to zero gap and matched against enumeration.
- `inputs/*.csv` — archived historical date's 41 incoming opportunities, 37 outward departures, selected full stop trajectories, 12 vehicle links, seven headway constraints, six individual shift bounds, assumptions.
- `results/enumeration_results.json` — results and scope caveats. Detailed per-opportunity comparisons and optimized shift schedule included.
- `Interim_Report_Draft_2026-11-06.docx` and `.pdf` — one-page draft, dated November 6 but citing November 13 as the revised deadline.
- `tests/test_scope_a.py`, `results/test_log.txt` — reproducibility/unit tests passed.

### Preliminary computational result

Under **assumed** 3-min passenger transfer, 3-min turnaround, +2-min different-berth repositioning, ±5-min departure shifts and headway deviations, and one-minute shift increments, exact exhaustive enumeration finds 71,673 feasible timetables. The **unique optimal** departure shift vector is `[-2, 0, -2, -1, +2, 0]` minutes, corresponding to 16:18, 16:50, 17:18, 17:49, 18:22, 18:52. Mean post-allowance wait changes **13.5122 -> 12.4634 minutes** (−7.76%); maximum wait **30 -> 27 minutes**. The waiting changes help 18 trips, harm 7, leave 16 unchanged. This is an exact result **for the assumed finite-grid model**, independently confirmed by SciPy/HiGHS at zero solver gap; it is not a completed Julia run or MBTA operational certification.

**Some results are model decisions, not observations:** 60-minute stranded penalty (unused here since fixed 19:20 service covers all 41); 3-min passenger allowance; 3-min scheduled turnaround; 2-min different-berth movement; and headway deviation ±5 minutes. No measured transfer passenger counts are used.

## Julia setup and execution (on a computer with Julia installed)

From this folder:

```bash
julia --project=. -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'
julia --project=. src/run_scope_a.jl
```

Or run `bash src/setup_and_run.sh`. The model should produce `results/jump_shift_schedule.csv`, `jump_optimized_connections.csv`, and `jump_selected_trip_stop_times.csv`. Check the solver objective **12.46341463414634 minutes** and shift vector `[-2,0,-2,-1,+2,0]` against `results/enumeration_results.json`.

## Independent Python check

Install Python 3 with NumPy, pandas, and SciPy, then run:

```bash
python src/reference_enumeration.py
python src/check_milp_with_scipy.py
python -m unittest discover -s tests -v
```

No external internet is required for these checks. The `inputs` CSVs are frozen from the earlier historical reconciliation; this package does not contain the 22-MB source GTFS ZIP. For a raw-to-CSV rerun, use the separately uploaded `20261014.zip` with `prepare_scope_a.py` and the adopted configuration.

## Completion vs pending

- Completed: full mathematical MILP definition, archived-input model tables, independently enumerated and SciPy/HiGHS-confirmed optimal finite-grid timetable, one-page interim report draft, Python tests.
- Prepared but **not executed in Julia**: solver script and post-solve checks. The next planned task is to install Julia and validate solution equivalence, then add a heuristic and sensitivity analyses.
- Unresolved operational question: whether the assumed berth movement/turnaround allowances reflect MBTA requirements. These remain assumptions with planned sensitivity analysis.
- Scope B remains out of scope until delay timestamps, date-specific feeds, and Quincy endpoint operations are validated.

**Important:** This is a research/analysis project, **not a software app**. The report is a team-review draft, not confirmation of a Gradescope submission.
