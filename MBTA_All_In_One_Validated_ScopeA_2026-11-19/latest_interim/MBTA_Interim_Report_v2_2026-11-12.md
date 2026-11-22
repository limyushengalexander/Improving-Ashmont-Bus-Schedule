# Improving MBTA Bus Transfers at Ashmont

6.C57 Optimization Methods | Interim progress report

Alex Lim | Yun Ji Seo | Luran Wang

Revised November 12, 2026 | Interim deadline: November 13, 2026

## Problem description

We study whether an MBTA service planner can reduce transfer waiting from Routes 22 and 23 to Route 215 toward Quincy Center by retiming six departures at Ashmont. Scope A covers arrivals from 4–7 p.m. on Thursday, October 15, 2026, assuming all buses run on time. Routes, trip counts, incoming timetables, and scheduled running times remain unchanged.

## Data

Historical MBTA GTFS records identify 18 Route 22 and 23 Route 23 terminal arrivals: 41 equally weighted transfer opportunities, not measured passenger counts. Relevant schedules and vehicle links were reconciled with the historical archive. All 37 eligible Route 215 departures are retained, including 10 after 7 p.m., to evaluate late-window transfers correctly. [1]

## Method and assumptions

A deterministic mixed-integer linear program selects departure shifts in one-minute increments within ±5 minutes, tightened by vehicle availability. Each selected trip’s full timetable moves consistently. The objective minimizes average waiting after an assumed three-minute walking/boarding allowance, using the earliest catchable onward bus. Constraints retain vehicle-block links and limit each affected headway’s change to ±5 minutes. We assume three minutes of turnaround plus two additional minutes for different-berth movements at Quincy Center; these are study assumptions, not verified MBTA operating requirements.

## Preliminary results

The preliminary optimized timetable reduces modeled mean waiting from 13.51 to 12.46 minutes: 1.05 minutes per opportunity, or 7.76%. The result is optimal on the specified one-minute grid under the adopted assumptions, not an estimate of observed passenger benefits. [2]

| Modeled measure | Existing | Optimized |
|---|---:|---:|
| Mean wait after transfer allowance | 13.51 min | 12.46 min |
| Maximum wait after transfer allowance | 30 min | 27 min |
| Opportunities with wait ≤10 minutes | 15 / 41 | 20 / 41 |

Four departures move: 16:20→16:18, 17:20→17:18, 17:50→17:49, and 18:20→18:22. Waiting decreases for 18 opportunities, increases for 7, and is unchanged for 16. Python enumeration of 71,673 feasible timetables and a SciPy/HiGHS MILP agree on this solution. Julia/JuMP source is prepared; execution remains pending. [2]

## Practical implications

Moving four departures by at most two minutes provides a modest scheduled benefit without adding trips in the model, making these changes candidates for planner review—not a deployment recommendation. The average improvement must be weighed against the seven worsened opportunities. Effects on other Route 215 riders and crew arrangements are not quantified; the result does not establish systemwide benefits or zero implementation cost.

## Next steps and expected outputs

Next we will execute the Julia model, compare it with a simple feasible retiming rule, and test transfer, turnaround, and berth-movement assumptions. These checks will establish whether optimization adds value beyond a simple rule and whether the benefit persists under alternative assumptions. Scope B remains deferred pending delay-data validation.

Sources: [1] MBTA historical GTFS, 20261014.zip; October 15 study extraction. [2] Project calculation records: enumeration_results.json and scipy_milp_crosscheck.json, November 6 model package.
