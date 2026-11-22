# 6.C57 Scope A: mathematical formulation and independent computational verification

**Project:** Improving Bus Transfer Connections at Ashmont Through Timetable Optimization
**Team:** Alex Lim, Yun Ji Seo, Luran Wang
**Study date:** Thursday, October 15, 2026, incoming terminal arrivals in [16:00,19:00)
**Revision:** November 6, 2026. **Status:** complete *finite-grid* formulation, Python exhaustive check executed; Julia/JuMP source supplied but **not executed** in this environment.
**MBTA operating status:** no claim of certification.

## 1. Decision and scope

Coordinate fixed incoming bus trips on Routes 22 and 23 with departure times of Route 215 toward Quincy Center. We do **not** add, remove, or reroute any trip. A selected Route 215 trip moves as a unit so its entire stop trajectory shifts consistently without changing its scheduled run or dwell durations. The model treats 41 incoming bus arrivals as *equally weighted potential transfer opportunities*, not observed transfer passenger counts.

The archived October 15 schedule was independently reconciled against the original starter snapshot. The relevant study records and vehicle-block links matched even though the complete GTFS feeds were not identical. See `inputs/feed_info.csv` and the separately supplied historical reconciliation package.

### Verified snapshot quantities

| Item | Quantity |
|---|---:|
| Route 22 inbound terminal arrivals | 18 |
| Route 23 inbound terminal arrivals | 23 |
| All potential incoming transfers | 41 |
| Selected Route 215 departures 16:00–19:00 | 6 |
| Eligible all-day Route 215 onward departures | 37 |
| After-19:00 onward departures | 10 |
| Original average waiting after 3-minute allowance | 13.5122 minutes |
| Original maximum post-allowance wait | 30 minutes |

## 2. Sets, data, and scenarios

- $I=\{1,\ldots,41\}$: selected incoming Route 22/23 trip opportunities.
- $J$: 37 eligible Route 215 departures on the selected service day, including after 19:00.
- $A\subset J$: six selected Route 215 departures, originally scheduled at 16:20, 16:50, 17:20, 17:50, 18:20, and 18:52.
- $K_j\subseteq\{-5,-4,\dots,5\}$: allowed *whole-minute* departure shifts for $j\in A$, after individual block-based bounds. For fixed $j\in J\setminus A$, $K_j=\{0\}$.
- $L$: 12 consecutive same-vehicle trip pairs touching a selected trip, including predecessor/successor trips on other routes. The surrounding trips are fixed.
- $H$: seven consecutive Route 215 departure pairs: six selected trips and their fixed immediate neighbors at 15:50 and 19:20.
- $a_i$: incoming scheduled terminal arrival in seconds after service-day midnight.
- $d_j$: scheduled Route 215 departure in service-day seconds.
- $\tau=180$ seconds: **assumed** combined walking/boarding/transfer allowance.
- $r_i=a_i+\tau$: earliest passenger boarding readiness. Equality with a departure is allowed.
- $g_{pq}$: scheduled gap (seconds) between same-block predecessor trip $p$'s end and successor trip $q$'s start; $m_{pq}$: assumed minimum gap for the pair.
- $h_{e\ell}=d_\ell-d_e$: baseline departure headway for adjacent Route 215 departures $(e,\ell)\in H$; bounds $\underline h_{e\ell}=h_{e\ell}-300$, $\overline h_{e\ell}=h_{e\ell}+300$ seconds.

Assumed operational requirements: **3-minute** scheduled turnaround at either end, plus **2 minutes** if a selected trip's following service begins at a different Quincy Center berth; departure adjustments no more than ±5 minutes; each affected headway deviation no more than ±5 minutes. These are research assumptions, not known MBTA minimums. The input files preserve each gap and `minimum_gap_sec`.

The integer-minute options from the checked vehicle bounds are:

| Scheduled departure | Allowed shift (minutes) |
|---|---|
| 16:20 | −2 to +1 |
| 16:50 | −2 to +5 |
| 17:20 | −2 to +4 |
| 17:50 | −2 to +5 |
| 18:20 | −2 to +5 |
| 18:52 | −4 to +3 |

These **individual** bounds are not enough by themselves: headways couple shifts between adjacent trips.

## 3. Finite-grid mixed-integer linear formulation

For each selected $j\in A$, let binary $z_{jk}=1$ when departure $j$ shifts by $k\in K_j$ minutes. The shift (in minutes) is expressed linearly as

$$
\sum_{k\in K_j}z_{jk}=1,\quad z_{jk}\in\{0,1\},\qquad x_j=\sum_{k\in K_j}kz_{jk}\quad(j\in A).
$$

For nonselected trips, $x_j=0$. Because each shift is an option with a known departure time, we can *precompute* catchable connection arcs:

$$
F_i=\{(j,k): j\in J,\ k\in K_j,\ d_j+60k\ge r_i\}.
$$

Let continuous $y_{ijk}\ge0$ represent transfer $i$'s assignment to arc $(j,k)\in F_i$, with *precomputed nonnegative cost* $c_{ijk}=d_j+60k-r_i$ seconds. Fixed trips have option $k=0$. Define the MILP:

$$
\begin{aligned}
\min \quad &\frac{1}{60|I|}\sum_{i\in I}\sum_{(j,k)\in F_i}c_{ijk}y_{ijk}\\
\text{s.t.}\quad &\sum_{(j,k)\in F_i}y_{ijk}=1, &&\forall i\in I,\\
&y_{ijk}\le z_{jk}, &&\forall i\in I,\ (j,k)\in F_i,\ j\in A,\\
&g_{pq}+60(x_q-x_p)\ge m_{pq}, &&\forall(p,q)\in L,\\
&\underline h_{e\ell}\le h_{e\ell}+60(x_\ell-x_e)\le\overline h_{e\ell},
&&\forall(e,\ell)\in H,\\
&\sum_{k\in K_j}z_{jk}=1,\quad z_{jk}\in\{0,1\}, &&\forall j\in A,\\
&x_j=\sum_{k\in K_j}kz_{jk}, &&\forall j\in A,\\
&x_j=0,&&\forall j\notin A,\\
&y_{ijk}\ge0.&&
\end{aligned}
$$

The expression is linear: both trip adjustment and transfer costs are selected from a finite list of constants. **No Big-M is required.** Conditional on the binary timetable decisions, the transfer assignments can be continuous because every eligible transfer has a nonnegative known cost. Minimization causes each opportunity to choose its earliest catchable departure. No capacity restriction or passenger rerouting benefit is assumed. A timetable never gets a fictitious zero-wait transfer if it cannot catch a bus.

### Why there is no optional stranded variable here

For this *specific* fixed October 15 cohort, the latest readiness is 18:58 and a **fixed** Route 215 departure exists at 19:20. Consequently, an eligible onward bus exists for every feasible $x$; there are no stranded opportunities, and no penalty is used in the model's objective. We retain the adopted **3,600-second penalty** for future cohorts with genuinely no onward service. In an extension, an unserved indicator must be **forced by the absence of any catchable departure**, never offered as a voluntary cheaper alternative.

### Whole-trip shift rule

For every GTFS stop $k$ on a selected trip $j$, the modeled time is its original time plus $60x_j$. This is enforced in output construction, so all scheduled running and dwell durations remain unchanged. The model checks both immediately preceding and following block links and all affected headways, including the fixed neighboring departures.

## 4. Computational implementation and validation

**Implemented source:** `src/run_scope_a.jl` is a JuMP/HiGHS MILP implementation with CSV/GTFS-derived inputs and an independent post-solve earliest-connection/vehicle/headway audit. Julia packages are listed in `Project.toml`. **Julia was not installed in the authoring environment**, so this file is delivered as runnable source, *not* claimed as a tested Julia solve.

**Independent computation:** `src/reference_enumeration.py` was executed against the historical-reconciled study CSVs. It enumerated all option combinations, tested the 12 vehicle and seven headway links, and evaluated the 41 opportunities for every feasible timetable. There are exactly **71,673 jointly feasible integer-minute timetables**. The *unique best* shift vector is

$$
(x_{16{:}20},x_{16{:}50},x_{17{:}20},x_{17{:}50},x_{18{:}20},x_{18{:}52})
=(-2,0,-2,-1,+2,0) \text{ minutes}.
$$

| Measure | Original schedule | Best finite-grid schedule |
|---|---:|---:|
| Mean waiting after transfer allowance | 13.5122 min | **12.4634 min** |
| Maximum post-allowance wait | 30 min | **27 min** |
| Opportunities waiting at most 10 min | 15/41 | **20/41** |
| Stranded | 0 | 0 |
| Total waiting over 41 opportunities | 554 min | **511 min** |

A **second, independently implemented SciPy/HiGHS MILP** (`src/check_milp_with_scipy.py`) was solved with **43 binary departure-option variables, 1,386 continuous eligible transfer-assignment variables and 1,042 linear constraints**. It returned the same unique shift vector and mean wait with **solver-reported zero MIP gap** (`results/scipy_milp_crosscheck.json`). This independently tests the MILP formulation, though it does **not** count as execution of the Julia/JuMP source.

Mean waiting decreases by **1.0488 minutes**, or **7.76%**. The best departures are 16:18, 16:50, 17:18, 17:49, 18:22, 18:52. Eighteen opportunities improve, seven worsen, and sixteen remain unchanged. This is an exact optimum **on the stated integer-minute grid and adopted feasibility rules**, not an MBTA-approved timetable or a Julia solve certificate. The model is sensitive to chosen allowances and schedules; the available passenger data do not support ridership-weighted claims.

### Additional verification tasks before interpreting recommendations

1. Run `julia --project=. src/run_scope_a.jl` after installing dependencies and compare the returned objective and shift vector with the independent exact enumeration (12.4634 min, six shifts above). Record solver termination status and bound/gap.
2. Add a transparent simple feasible heuristic and compare on the same objective and constraints.
3. Repeat transfer allowance (2, 3, 5 minutes), shift cap (±2, ±5 minutes), turnaround (2, 3, 5 minutes), berth movement (0, 2, 3 minutes). Flag cases where the existing timetable fails a tighter assumption, rather than claiming a comparable baseline.
4. Explain the effect on individual arrivals, affected other routes, and absent passenger counts. The model is a narrow **timetable coordination analysis**, not a service deployment or app.
5. Scope B is not part of this implementation. Historical delay clocks, observation dates, and Quincy vehicle end/start observations will be validated separately when Scope B begins.

## 5. Sources and audit

- MBTA historical archived feed entry: `20261014.zip`, version `Fall 2026, 2026-10-21T20:52:18+00:00, version D`, user provided; historical GTFS archive index: https://cdn.mbta.com/archive/archived_feeds.txt
- MBTA GTFS documentation: https://github.com/mbta/gtfs-documentation/blob/master/reference/gtfs.md
- Internal project record: `MBTA_Historical_GTFS_Reconciliation_2026-11-06.zip`, `MBTA_ScopeA_Oct23-29_Closure.zip`, and `inputs/adopted_scope_a_config.json`.
- JuMP and HiGHS documentation: https://jump.dev/JuMP.jl/stable/tutorials/getting_started/getting_started_with_JuMP/
- Data provenance: each `inputs/` CSV is from the archived GTFS reconciliation previously computed. No additional raw MBTA observations were collected for Scope A today.
