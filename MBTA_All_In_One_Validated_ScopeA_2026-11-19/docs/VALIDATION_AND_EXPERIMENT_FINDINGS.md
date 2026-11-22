# Scope A validation and experiment findings
**Run date: November 19, 2026. Team: Alex Lim, Yun Ji Seo, Luran Wang.**

Working evidence memo, not the final course report. All new calculations below were executed in Python against the uploaded, historically reconciled October 15 inputs. No new MBTA observations were acquired. Julia was not installed and downloading the official runtime failed; **no Julia execution certificate is claimed**. Original archives and the latest interim report are preserved unchanged.

## 1. Executive findings

The original scheduled-case finding reproduces: 41 equally weighted incoming-trip opportunities have mean waiting after a three-minute allowance of **13.5122 minutes** in the original timetable and **12.4634 minutes** under shifts **[-2, 0, -2, -1, +2, 0] minutes**. This is a reduction of **1.0488 minutes (7.7617%)**. The maximum waiting falls from 30 to 27 minutes. Both fresh exhaustive enumeration and a fresh SciPy/HiGHS MILP reproduce the saved result.

Two additional conclusions change how the result should be presented:

1. A prespecified, simple, feasible chronological retiming rule reaches **the same timetable and objective**. It also matches the optimum in all 32 feasible cases tested (including diagnostic relaxations). The tested cases do **not** establish incremental performance gains from the MILP over that heuristic. The MILP supplies an optimality certificate and a consistent experimental framework, not a demonstrated additional service improvement over the simple rule on these instances.
2. The timetable is **not insensitive to the transfer allowance**. At a five-minute allowance, the original timetable averages 13.6585 minutes, whereas the unchanged three-minute-optimal timetable averages **15.6829 minutes**. Reoptimization for five minutes gives **11.8537 minutes**. A parameter-specific optimum and a robust fixed recommendation are different claims.

## 2. Baseline protection and data review

All eight uploaded ZIP archives passed CRC checks. SHA-256 records are in `validation/source_zip_hashes.json`. The official historical archive was reprocessed using the uploaded preparation script and adopted config. Eight comparable files matched the model input copies byte for byte: `incoming.csv`, `outgoing.csv`, `vehicle_links.csv`, `headway_limits.csv`, `block_trip_endpoints.csv`, `selected_trip_stop_times.csv`, `baseline_connections.csv`, and `feed_info.csv`.

The reproduced data contains 18 Route 22 arrivals, 23 Route 23 arrivals, 37 all-day Route 215 departures, six selected adjustable trips, and ten departures at/after 19:00. All shifts apply to the complete selected trip. Both fixed boundary departures (15:50 and 19:20) are included in the seven affected headway pairs. The 12 vehicle links include fixed predecessors and successors on other routes.

The raw preparation script intentionally retains its generic `PROVISIONAL_REQUIRES_REVIEW` status because operating allowances are not certified and the script itself does not check online historical applicability. The earlier archived-feed reconciliation remains separate evidence; the current extraction did not substitute a live feed or silently edit provenance flags.

The unchanged nominal inputs are locked in `validation/baseline_lock.json`. The original archives remain under `source_archives/`; old recorded results are separately retained in `validation/original_recorded_results/`. New results never overwrite those source records.

## 3. Model and code review

The inspected formulation is the finite-grid MILP already described in the project. Binary variables choose one allowed shift per selected trip; nonnegative transfer assignments can only use selected and catchable departures. The objective minimizes the mean post-allowance wait over the same 41 arrivals. Vehicle-gap and headway constraints couple timetable choices. No capacity constraint or passenger-demand model is present.

The continuous connection assignments do not invalidate the nominal model. For a fixed timetable, each opportunity can select a minimum-cost eligible departure; ties could split assignments without reducing the true minimum. A separate evaluator always reports the earliest actual eligible departure. The fixed 19:20 service covers even the latest readiness in every executed case, so none relies on an optional stranded penalty.

### Source changes and limitations

The November 12 patch was applied to the actual uploaded Julia source, creating `model/src/run_scope_a_reviewed.jl`. The original `run_scope_a.jl` is retained. Explicit String types preserve timetable clock fields, including service-day times beyond midnight. The reviewed source records solver status, requires a feasible primal result, and distinguishes a time-limited incumbent from a proven optimum. Additional non-mathematical edits save baseline connections and request zero relative MIP gap. A complete diff is supplied.

`Project.toml` is an application dependency environment rather than a named library package without a module entry file. Its original metadata is retained in `validation/Project_original.toml`. No resolved Manifest was invented: it must be generated and saved during actual Julia installation. These are reviewed source changes, **not execution-verified Julia fixes**.

The nominal Julia source is intentionally not used as a generic sensitivity runner: it has fixed-cohort assertions and reads frozen bounds. The new Python experiment engine rebuilds option domains and constraint right-hand sides from raw scheduled gaps and declared case parameters, avoiding stale-bound comparisons.

## 4. Benchmark definition and outcome

The heuristic was specified in `experiments/experiment_plan.json` before executing the new suite:

Start at the original timetable. Visit the six adjustable departures once, in original chronological order. For the current departure, inspect its allowed whole-minute shifts while holding the other five at their current values. Reject any complete-timetable vehicle/headway violation. Accept a change only when total waiting strictly decreases. For equally good improving changes, prefer the smallest absolute shift, then the earlier departure. Do not revisit previous departures or consult the optimizer's solution.

| Method | Mean wait after allowance | Maximum wait | Waiting <=10 min | Stranded |
|---|---:|---:|---:|---:|
| Existing timetable | 13.5122 min | 30 min | 15/41 | 0 |
| Single chronological pass | 12.4634 min | 27 min | 20/41 | 0 |
| MILP / exact enumeration | 12.4634 min | 27 min | 20/41 | 0 |

The primary heuristic makes 38 evaluations including its starting evaluation and repeated/current-timetable checks. A supplementary repeated-pass version terminates after a second pass with no further improvement. Neither result was selected from a search for an artificially weak comparator.

The nominal solver uses 43 binary options, 1,386 continuous assignment variables and 1,042 constraints. Its new objective and bound both equal 30,660 total waiting seconds, with zero reported gap. Exhaustive enumeration checks 71,673 feasible timetables and finds one optimum. The exact objective is in total seconds in the new solver implementation; dividing by 41 and 60 gives the same mean-minute objective as the original model. Runtime fields describe single executions on this environment and are not a controlled algorithm-speed benchmark.

## 5. Experiment design and coverage

**38 declared cases** were run: a 27-case crossing of transfer allowance {2,3,5 min}, turnaround {2,3,5 min}, and extra berth movement {0,2,3 min}; two departure caps; three additional headway tolerances; two readiness-boundary checks; one 30-second grid check; and three diagnostic constraint removals. The nominal case is part of the 27, not an extra duplicate.

There are **32 optimal feasible cases** and **six infeasible cases**. All 32 MILPs report zero gap. Independent exhaustive enumeration confirms 31 optima; the half-minute grid is solver-verified and independently evaluated but not exhaustively enumerated because its full option product exceeds the preset two-million-combination limit. Neither grid establishes global optimality for arbitrary continuous departure times.

For every case we separately record the original timetable, the newly optimized timetable, the feasible heuristic (only if its zero-shift start is feasible), and the **unchanged nominal optimum**. Infeasible comparisons are labeled, and no percent benefit is assigned to an infeasible baseline.

### A. Passenger transfer allowance

Turnaround remains three minutes, berth movement two minutes, and nominal shift/headway limits remain unchanged.

| Allowance | Existing mean wait | Reoptimized mean wait | Unchanged nominal-optimum mean wait |
|---|---:|---:|---:|
| 2 min | 14.5122 | 12.7073 | 13.4634 |
| 3 min | 13.5122 | 12.4634 | 12.4634 |
| 5 min | 13.6585 | 11.8537 | 15.6829 |

These are waiting **after** the allowance. For total arrival-to-departure transfer time, add the allowance to each value. A lower post-allowance number across different allowances does not automatically mean a shorter transfer: the five-minute reoptimized total is 16.8537 minutes versus 15.4634 minutes at three minutes. The proper comparison of original and optimized schedules is within the same allowance.

Seven nominal-optimized opportunities are ready exactly when their selected departure leaves, compared with two under the original timetable. Changing only the allowance from 180 to 181 seconds makes the unchanged optimal timetable average **17.6663 minutes**, versus **14.9102 minutes** for the original schedule; reoptimization obtains **13.0809 minutes**. This is a deterministic boundary diagnostic, **not a prediction that real buses incur a specific delay or a measured reliability estimate**. It shows that the equality-catch convention and transfer allowance materially drive recommendations.

### B. Vehicle allowance sensitivity and infeasibility

With two-minute scheduled turnaround and two-minute berth movement, the reoptimized mean is 12.1707 minutes. Under the nominal three-minute turnaround, changing extra berth movement among 0, 2 and 3 minutes leaves the nominal optimum and objective unchanged, even though the feasible set changes.

Five-minute turnaround plus two or three minutes of berth movement makes the **entire fixed-neighbor problem infeasible**, for each tested passenger allowance. The 16:20 vehicle has five minutes before departure and six after its selected trip. A five-minute predecessor requirement forces `x >= 0`; a five-plus-two-minute successor requirement forces `x <= -1 min`. Both cannot hold. This is a structural inconsistency in the stricter assumed rules with the fixed schedule, not a data gap or solver failure. Five-minute turnaround with zero extra berth movement remains feasible, but the nominal earlier-departure choices do not satisfy that stricter turnaround rule.

### C. Departure movement, service spacing and grid resolution

| Change from nominal assumptions | Reoptimized mean wait | Interpretation |
|---|---:|---|
| No departure shifts permitted | 13.5122 | Recovers the status quo |
| Departure shifts limited to +/-2 min | 12.4634 | Retains the full nominal improvement |
| No headway changes permitted | 13.5122 | Fixed boundary departures force all six shifts to zero |
| Headway deviation limited to +/-2 min | 12.5122 | Slightly less improvement than nominal |
| Nominal headway deviation +/-5 min | 12.4634 | Main case |
| Headway deviation +/-10 min | 12.3902 | Only 0.0732 min additional gain per opportunity |
| 30-second rather than 60-second shift grid | 12.4634 | No better objective in this finer-grid test |

### D. Diagnostic constraint removal (not implementable recommendations)

Removing vehicle constraints gives 11.7805 minutes but violates three of the full model's vehicle gaps. Removing headway constraints gives 12.3902 minutes but creates a 36-minute headway where the nominal rule allows at most 35. These tests show the practical cost of the modeled rules. A constraint can exclude a better alternative even if it is not tight at the original integer optimum; no nominal headway bound is tight, yet removing the family improves the objective.

## 6. Distribution and interpretation

The main timetable improves 18 opportunities, worsens seven by exactly two minutes each, and leaves 16 unchanged. The largest single improvement is 30 minutes: the Route 23 arrival at 18:19 becomes ready at 18:22, catching the retimed 18:22 departure instead of 18:52. This single opportunity accounts for 30 of the 43 net minutes saved across equal-weight arrivals. That concentration is relevant because actual transfer passenger counts are absent.

| Incoming route | Opportunities | Original mean | Optimized mean | Sum of modeled waiting saved |
|---|---:|---:|---:|---:|
| 22 | 18 | 12.8889 min | 12.5000 min | 7 min |
| 23 | 23 | 14.0000 min | 12.4348 min | 36 min |

All 300 stop-time rows for the six selected trips shift consistently without shortening dwell or running times. All 33 consecutive trip pairs in the affected vehicle blocks retain nonnegative time gaps. The adopted minimum-buffer requirements are checked on the 12 links touching adjusted trips; the other 21 unchanged links are checked for overlap, not certified against undocumented operating policies.

Managerial conclusion: modest coordination can help under the nominal scheduled assumptions, and a simple rule is sufficient for the tested instance. A +/-2-minute policy retains the nominal optimum. The particular nominal timetable should not be labeled robust to transfer uncertainty. Operational allowances, effects on other Route 215 riders, capacity, crews, and actual delays remain outside the evidence used here.

## 7. Verification status and reproducibility

Fresh runs passed **12 original tests and 34 new tests**. In addition, a separate brute-force earliest-departure check verified **5,740 opportunity/case/timetable rows**, including status quo, reoptimized, heuristic and frozen-timetable comparisons. The new tests check domain regeneration, equality behavior, late service, forced stranding in synthetic edge cases, baseline feasibility, headway and vehicle constraints, full-trip shifts, immutable input hashes and reported case status.

Executed: archive reconstruction, original enumeration/MILP reruns, primary/supplementary heuristics, 38-case suite, individual effects, constraint/trajectory audits, tests and figures.

Not executed: Julia/JuMP (runtime unavailable and official download unsuccessful), Scope B, new data collection, final report/slides/video production. The November 12 interim report is copied unchanged as a historical deliverable; these newer findings do not silently rewrite it.

To reproduce with Python, install the versions in `requirements-python.txt`, then run:

```bash
python model/src/reference_enumeration.py
python model/src/check_milp_with_scipy.py
python -m unittest discover -s model/tests -v
python experiments/scope_a_experiments.py
python experiments/summarize_and_audit.py
python -m unittest discover -s tests -v
python experiments/make_figures.py
```

To finish Julia verification on a machine with Julia, run `model/src/setup_and_run_reviewed.ps1` on Windows, or `bash model/src/setup_and_run_reviewed.sh` on macOS/Linux. Keep the generated Manifest, environment log, solver summary, CSV outputs and console log. Then run `python validation/verify_julia_outputs.py`. It refuses to certify a run when actual Julia outputs are missing.

## 8. Sources and authorship

Input evidence is the eight uploaded archives, especially the October 15 historical feed, November 6 model package, and November 12 revision. Exact source filenames and hashes are in `validation/source_zip_hashes.json`. Online sources were limited to official Julia, JuMP and Pkg documentation for runtime/setup and solution-status handling; no online timetable or observations replaced the uploaded data. See `docs/source_register.json`.

This working memo, code changes, experiment execution and packaging are AI-assisted technical work. Original provenance is retained. The team must review and understand the analysis and follow the course's authorship/disclosure requirements; this is not presented as an independently authored final student submission.
