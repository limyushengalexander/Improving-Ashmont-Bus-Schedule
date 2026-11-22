# MBTA Ashmont project: what we have done and how the model works

**An explained project guide, prepared November 22, 2026**

We prepared the scheduled-service data, checked its historical source, formulated an optimization problem, solved it using two Python-based methods, and prepared a revised one-page interim report. Under the adopted assumptions, the best timetable reduces average modeled transfer waiting from **13.5122 to 12.4634 minutes**. The optimization has been performed; running and verifying the separate Julia/JuMP implementation remains unfinished.

This guide follows the sequence of your pasted summary and incorporates the questions you raised. Questions appear above their explanations. Sections 1–8 explain the work through the **November 12 interim report**, with later verification identified where relevant. Section 9 updates the remaining-work list using the **November 19 findings**: the heuristic comparison and sensitivity experiments have since been completed in Python.

This is a new explanatory document in the extracted working copy. It does not replace the original formulation, interim report, saved results, or reference ZIP. No new optimization was run to prepare this guide. Numerical results below come from the saved project records. Open this file in **VS Code Markdown Preview** to render the equations.

## 1. What problem are we trying to solve?

Imagine a passenger arriving at Ashmont on Route 22 or 23. They want to continue toward Quincy Center on Route 215. If that bus leaves just before they can reach it and board, they may face a long wait for the next departure.

Our planning question is:

> Can small changes to Route 215's departure times improve these transfers while preserving the number of trips, the routes, and feasible vehicle schedules?

| Part of the study | Our choice |
|---|---|
| Transfer location | Ashmont |
| Incoming services | Routes 22 and 23 |
| Onward service | Route **215**, toward Quincy Center |
| Service date | Thursday, October 15, 2026 |
| Incoming study window | 16:00 up to, but not including, 19:00 |
| Timetable decisions | Shifts to six selected Route 215 trips |
| Incoming schedules | Fixed |
| Routes and number of trips | Fixed |
| Selected trips' running and dwell durations | Fixed; their entire schedules move together |
| Scope A operating condition | Buses operate at the modeled scheduled times |
| Performance measure | Average waiting after an assumed three-minute transfer allowance |

### “For the optimization itself, is everything based on scheduled data?”

Yes: the nominal Scope A optimization uses **scheduled arrival/departure times and scheduled vehicle assignments**, together with adopted modeling assumptions. Its reported improvement does not come from fitting a model to observed bus delays.

Scope A asks what timetable coordination can accomplish under an on-schedule operating condition. That makes it possible to isolate the effect of departure changes. Whether those benefits survive real delays is a separate question, discussed in Section 9.

### “What are opportunities? Are we assuming full buses? Would demand matter?”

One **transfer opportunity** means one incoming bus trip whose passengers could potentially transfer to Route 215. We count that incoming trip once, regardless of whether it carries one transferring passenger, twenty, or none. We do not have validated transfer-passenger counts for weighting the analysis.

We therefore give all 41 incoming opportunities equal weight. This is not a full-bus assumption, and it is not a claim that there are 41 passengers. The model assumes the represented transfers can board a catchable onward bus; it does not impose bus capacity or crowding restrictions.

Demand could change the recommendation. If one opportunity represented 50 transferring passengers and another represented one, reducing the first group's wait might deserve more weight. With known passenger counts $p_i$, an alternative objective would be:

$$
\frac{\sum_i p_i w_i(x)}{\sum_i p_i}.
$$

Here $w_i(x)$ is that group's waiting time under timetable $x$. Our current model uses equal weights instead. Consequently, its 7.76% improvement is an **opportunity-weighted modeled improvement**, not a measured reduction in total passenger waiting.

### “What is an objective versus an objective function?”

The **objective** is the goal: reduce average transfer waiting.

The **objective function** is the formula that scores a proposed timetable: add the 41 waiting times and divide by 41.

The **objective value** is the number obtained for a particular timetable: for example, 13.5122 minutes for the original schedule or 12.4634 minutes for the best permitted schedule.

Data are the information we take as given. Decision variables represent choices we can make. Constraints are the rules those choices must satisfy. Optimization searches for the permitted choices with the best objective value.

## 2. Step one: turning the raw timetable into usable data

### “What was in the starter file? What does ‘what buses were estimated to have done’ mean?”

The starter materials contained two different kinds of information:

| Information | What it tells us | Role in this project |
|---|---|---|
| GTFS timetable snapshot | What service was scheduled: routes, trips, stops, times, and planned vehicle blocks | Main basis for Scope A |
| Operational bus-event estimates | Estimates of when buses actually reached or left recorded stops | Earlier data-quality audits and diagnostic work; possible input to a later delay analysis |

For example, a timetable might say “this trip arrives at 18:19.” An event estimate might say “the recorded operational data suggest that trip arrived around 18:23.” Those are different claims.

The event records are operational observations, but the recorded times are estimates with coverage and interpretation limitations. They should not automatically be treated as perfect measurements of every bus movement.

### “Did we never use actual operational data at all?”

Operational records were examined in the earlier preparation work. That work checked coverage, missing arrival/departure estimates, timestamp interpretation, trip matching, and some observed vehicle gaps. It also produced conditional diagnostic replays.

The supplied Ashmont event extract contained **3,427 rows**, covering selected routes and dates from October 10–16. It had missing estimates, an identified four-hour inconsistency between timestamp representations, and no Quincy endpoint observations for the full vehicle analysis. The diagnostic replays were explicitly qualified; they were not a validated Scope B result.

Thus, operational data helped us understand data limitations and possible future work. **They did not supply the arrival/departure values used to obtain 13.5122 or 12.4634**, and the later Scope A parameter experiments did not become observed-delay experiments merely because event data existed elsewhere in the package.

### “Why could we calculate the on-time baseline without resolving historical delays?”

Because the on-time baseline asks a conditional question: **if the selected buses follow the schedule, how long would these transfers wait under our allowance?** Scheduled times are sufficient to answer that question.

Resolving actual delays is necessary for a different question: how long people were likely to wait in observed operation, or how a proposed timetable performs when buses run late. We have not equated the scheduled baseline with either of those outcomes.

### “Where do 41, 37, and six come from?”

| Count | What is being counted |
|---:|---|
| 18 | Route 22 trips arriving at Ashmont in the incoming study window |
| 23 | Route 23 trips arriving at Ashmont in the incoming study window |
| **41** | Those 18 + 23 incoming opportunities |
| **37** | Eligible Ashmont-to-Quincy Route 215 departures across the selected service day |
| **6** | Departures among those 37 selected for adjustment because their original departure times fall within 16:00–19:00 |
| 31 | Remaining eligible Route 215 departures, whose times are fixed |

The six adjustable departures are **16:20, 16:50, 17:20, 17:50, 18:20, and 18:52**. Data preparation identified them by selecting service active on the study date, the correct route and direction/destination, departures from Ashmont, boarding eligibility, and the departure window. The optimizer did not choose how many trips to include.

The 41 and 37 count different things. There are no “last four” obtained by subtracting 37 from 41. Several incoming opportunities can connect to the same onward departure.

For example, the original schedule sends the following three opportunities to the **same 16:20 Route 215 departure**:

| Incoming trip | Ashmont arrival | Ready after three minutes | Onward departure | Waiting after readiness |
|---|---|---|---|---:|
| Route 22 | 16:05 | 16:08 | 16:20 | 12 min |
| Route 23 | 16:08 | 16:11 | 16:20 | 9 min |
| Route 22 | 16:15 | 16:18 | 16:20 | 2 min |

Passengers transfer between buses. This does **not** mean three incoming buses become the onward bus, or that six of the 41 incoming vehicles are selected to operate Route 215.

### “Why are departures after 19:00 included?”

The window selects incoming arrivals and adjustable departures. It does not prohibit a passenger arriving near 19:00 from catching a later bus.

Ten of the 37 eligible onward departures occur after 19:00. Two baseline opportunities use the fixed **19:20** departure. Removing later service would misrepresent their available connections.

### “What do the input files mean? Were there six key files?”

The earlier summary referred to six checked files without naming an auditable six-file subset. The later November 19 reproduction explicitly documents **eight matching input files**. The table below names that verified set rather than guessing which six the earlier wording intended.

| File in `model/inputs/` | Plain-language meaning |
|---|---|
| [incoming.csv](../model/inputs/incoming.csv) | The 41 incoming scheduled terminal arrivals |
| [outgoing.csv](../model/inputs/outgoing.csv) | The 37 eligible onward departures, including which six may move |
| [vehicle_links.csv](../model/inputs/vehicle_links.csv) | Consecutive trips assigned to the same scheduled vehicle block; these limit trip shifts |
| [headway_limits.csv](../model/inputs/headway_limits.csv) | Allowed spacing between affected consecutive Route 215 departures |
| [selected_trip_stop_times.csv](../model/inputs/selected_trip_stop_times.csv) | Every scheduled stop-time row along each of the six selected trips |
| [baseline_connections.csv](../model/inputs/baseline_connections.csv) | Which onward departure each incoming opportunity catches in the original timetable, and its waiting time |
| [block_trip_endpoints.csv](../model/inputs/block_trip_endpoints.csv) | Start/end locations and times for trips in the six affected vehicle blocks |
| [feed_info.csv](../model/inputs/feed_info.csv) | Metadata identifying the adopted GTFS feed |

A **connection** in `baseline_connections.csv` means a passenger transfer from an incoming trip to an onward departure. A **vehicle link** means a bus finishing one scheduled assignment and starting another. These are different relationships.

### “Does `selected_trip_stop_times.csv` include stops before Ashmont? How many stops are there to Quincy?”

For these selected trips, Ashmont is the first stop and Quincy Center is the final stop. The file contains **300 rows: six trips with 50 stop entries each**. Each selected trip has 48 intermediate stops and 49 stop-to-stop segments. It does not include the bus's preceding trip before reaching Ashmont.

| Original Ashmont departure | Scheduled Quincy arrival | Scheduled duration |
|---|---|---:|
| 16:20 | 17:08 | 48 min |
| 16:50 | 17:38 | 48 min |
| 17:20 | 18:05 | 45 min |
| 17:50 | 18:29 | 39 min |
| 18:20 | 18:57 | 37 min |
| 18:52 | 19:29 | 37 min |

Therefore “48 minutes over 49 segments” describes the first two selected scheduled trips. It does not describe all six, imply equal time per segment, or establish observed travel time. Scheduled running and intermediate stopping time are part of the trip duration.

### “What is a scheduled block? Is `block_id` a bus ID?”

A block is a sequence of trips **planned to be operated by one vehicle**. A block identifier describes that planned work sequence; it is not the permanent fleet number of a particular physical bus.

For example, the schedule assigns these consecutive jobs to block `Q215-56`:

| Job | Route | Scheduled movement |
|---|---|---|
| Preceding trip | 215 | Quincy Center Berth 3, 15:35 → Ashmont, 16:15 |
| Selected trip | 215 | Ashmont, 16:20 → Quincy Center Berth 3, 17:08 |
| Following assignment | 220 | Quincy Center Berth 4, 17:14 → Hingham Depot, 17:51 |

The planned vehicle must finish each job in time to perform the next one. A late departure from Ashmont also delays its Quincy arrival, even though the following Route 220 trip remains fixed.

The six **affected blocks** are the blocks containing the six adjustable trips. Their endpoint table contains 39 trips in total, including other routes. Only 12 consecutive links directly touch an adjustable trip; we explain all 12 in Section 5.

### “Are the Route 22/23 buses reused on Route 215? Have we confirmed Route 215 becomes Route 220?”

The scheduled blocks do not link the 41 incoming trips to the six selected outgoing trips. The broader check of the selected day's active schedule also found no shared Route 22/23 blocks with Route 215. This supports treating incoming passenger transfers separately from the selected vehicles' work sequences.

For the **16:20 selected Route 215 trip**, the schedule explicitly links its vehicle to the following Route 220 trip shown above. That establishes the planned assignment. We do not have the Quincy/Route 220 operational observations needed to establish that the exact same physical vehicle performed both jobs on that day. Vehicle substitution in actual operations is a separate matter.

Do not generalize this into “Route 22/23 vehicles can never work Route 215” or “every Route 215 trip next becomes Route 220.” The selected trips have different successors.

### “After the 18:20 and 18:52 trips reach Quincy, do they return to Ashmont?”

Yes, according to their next scheduled assignments:

| Selected outward trip | Arrival at Quincy Berth 3 | Next scheduled trip | Next departure | Arrival back at Ashmont |
|---|---|---|---|---|
| Route 215, 18:20 from Ashmont | 18:57 | Route 215 toward Ashmont | 19:05 | 19:36 |
| Route 215, 18:52 from Ashmont | 19:29 | Route 215 toward Ashmont | 19:35 | 20:02 |

The selected outward trips end at Quincy. The returns are separate trips in the same planned vehicle blocks; they are not extensions of the outward trip's 50-row stop sequence.

## 3. Step two: checking the historical schedule and documenting assumptions

### “What is the difference between the starter GTFS snapshot and the historical archive?”

Both contain scheduled-service data. They are different versions of that data.

The starter's `MBTA_GTFS_2026-10-16.zip` was a snapshot of the then-current feed. Its metadata identified a version timestamp of October 14. The historical `20261014.zip` was the archive selected for the October 14–19 service period, with a **retrospective revision timestamp of October 21**. Its filename should not be mistaken for its publication timestamp.

Historical reconciliation checked whether using the archived version changed the study's extracted trips, times, and vehicle relationships. Although the complete feeds differed, **16 of 17 compared preparation outputs matched**; the different output was feed metadata.

The November 19 reproduction made a different comparison: it rebuilt the study inputs from the **already adopted historical source** and compared them with the saved model inputs. All **eight files listed in Section 2 matched byte for byte**, including metadata. These findings are consistent because the two comparisons use different pairs of sources.

### “Does that validate our use of actual data or prove buses ran on time?”

It validates the consistency and reproducibility of the **scheduled input extraction**. The schedule is real agency data, but it records intended service.

Byte-for-byte agreement says that reconstructing the inputs from the adopted archive produces the same files. It does not compare those times with observed arrival times. A bus can have a perfectly documented 18:19 scheduled arrival and actually arrive at 18:23.

The later reproduction evidence is recorded in [baseline_reproduction.json](../validation/baseline_reproduction.json).

### “Which numbers are assumptions, and why did we choose them?”

| Assumption | Meaning | What it controls |
|---|---|---|
| Three-minute passenger transfer allowance | Time between incoming arrival and readiness to board the onward bus | Which departures passengers can catch |
| Three-minute vehicle turnaround allowance | Minimum modeled gap between consecutive assignments of the same vehicle | Vehicle availability |
| Two additional minutes for a different Quincy berth | Extra modeled repositioning time after a selected trip | Minimum vehicle gap becomes five minutes for those links |
| Maximum departure shift ±5 minutes | Initial cap on moving an adjustable trip earlier or later | Size of permitted timetable changes |
| Whole-minute adjustment grid | Allowed shifts use complete minutes | The finite set searched |
| Headway deviation at most ±5 minutes | Each affected gap between departures may change by no more than five minutes | Service spacing |
| Whole-trip movement | All selected trip stop times change by the same amount | Preserves scheduled run and dwell durations |

These are **adopted research assumptions** in the [configuration](../model/inputs/adopted_scope_a_config.json), not verified MBTA operating minima. The numbers define a manageable small-retiming study. There is no documented measurement proving that exactly three or five minutes is the correct universal value. That is why we later varied these assumptions in sensitivity experiments.

The two three-minute allowances serve different purposes. Passenger transfer time concerns people moving between services. Vehicle turnaround concerns a vehicle finishing one job and becoming available for another. Neither should be substituted for the other.

Likewise, a ±5-minute departure cap controls **one trip's shift**. A ±5-minute headway limit controls **the change in the gap between two trips**. Individually permitted shifts can still create an unacceptable gap when combined.

### “Berth versus bus bay? Is the three-minute allowance specifically for moving from bays 7/8 to bay 1?”

In this context, a berth or bay is a designated place within a terminal where a bus stops for boarding/alighting. A station can contain several such positions.

The supplied GTFS identifies the selected Ashmont endpoint as stop `334`, “Ashmont – Busway,” without resolving individual numbered bays. Quincy is more detailed: the selected Route 215 trips end at **Berth 3**, while some following assignments start at Berths 1, 2, or 4. Those known Quincy stop differences are used in the vehicle constraints.

Earlier public-map checks suggested Route 22 boarding at Berth 7, Route 23 at Berth 8, and Route 215 at Berth 1. Those were provisional, nonagency boarding-location indications; they did not verify where arriving Route 22/23 passengers actually alighted on October 15. An advertised boarding bay also need not establish an arriving trip's alighting position.

Accordingly, the three-minute allowance represents combined alighting, walking, boarding, and transfer preparation. It was **not measured as a verified walk from bays 7/8 to bay 1**. Better terminal-path and alighting-location evidence could support a more precise allowance later.

### “Was the extra two minutes at Quincy actually used?”

Yes. A selected trip followed by a service at a different Quincy berth has a modeled minimum gap of **3 + 2 = 5 minutes**. A same-berth successor requires three minutes. This appears in the vehicle-link inputs, the individual shift bounds, and the vehicle-availability constraints. It directly limits the 16:20 trip's latest allowed departure, as Section 5 demonstrates.

## 4. Step three: calculating the existing timetable's performance

### “What does 13.5122 minutes mean? Is that how long the bus waits?”

It is the **average modeled passenger wait after the transfer allowance**. It does not measure a bus waiting or laying over at the terminal.

For each incoming opportunity, we perform these steps:

1. Read its scheduled Ashmont arrival time.
2. Add the three-minute transfer allowance to obtain passenger readiness.
3. Find the first eligible Route 215 departure at or after readiness.
4. Subtract readiness from that departure time.

In symbols, using minutes throughout:

$$
r_i=a_i+3,
\qquad
\text{waiting}_i=\text{departure caught}_i-r_i.
$$

Here $a_i$ is the incoming arrival and $r_i$ is the readiness time. There is one arrival value for each of the 41 opportunities, although different trips could share the same clock time.

### “Is 16.5122 minutes the bus's journey from Ashmont to Quincy?”

No. It is the average **total transfer time at Ashmont**, from incoming arrival to onward departure:

$$
\text{total transfer time}_i
=\text{departure caught}_i-a_i
=3+\text{waiting}_i.
$$

The onward bus journey begins after this transfer time ends. For example, the original 16:20 departure's scheduled 48-minute ride to Quincy is a separate measure.

The baseline's average post-allowance wait is 13.5122 minutes. Adding the same three-minute allowance for every opportunity gives **16.5122 minutes** average total transfer time. These are averages: they do not mean every passenger group waits that long.

### “Can you show the waiting calculation using an actual study row?”

One scheduled Route 23 arrival is **18:19**. Its passengers become ready at **18:22**.

| Timetable | What happens | Waiting after readiness | Total transfer time |
|---|---|---:|---:|
| Original | The 18:20 departure is already gone; catch 18:52 | 18:52 − 18:22 = **30 min** | 18:52 − 18:19 = **33 min** |
| Optimized | The original 18:20 trip moves to 18:22 and is catchable | 18:22 − 18:22 = **0 min** | 18:22 − 18:19 = **3 min** |

The model allows boarding when readiness exactly equals departure. Zero waiting therefore means no additional waiting **after** the allowance; it does not mean instantaneous transfer from one bus to another.

Another scheduled Route 23 arrival is **17:52**, ready at **17:55**. That opportunity originally catches 18:20 and waits 25 minutes. When that trip moves to 18:22, its wait becomes 27 minutes. The same change helps the first opportunity by 30 minutes and worsens the second by two minutes.

This is why the model evaluates **all 41 opportunities together**, instead of improving one connection without considering its consequences for others.

### “Where exactly does the baseline average come from?”

The saved original connections have total waiting of **554 opportunity-minutes**: 232 for Route 22 opportunities and 322 for Route 23 opportunities.

$$
\text{Baseline mean wait}=\frac{554}{41}=13.512195\ldots\text{ minutes}.
$$

The baseline maximum is 30 minutes, 15 of the 41 opportunities wait at most ten minutes, and none is stranded. Calculating this baseline evaluates the original schedule; optimization is the additional step of searching for a better permitted schedule.

Sources: [original connections](../model/inputs/baseline_connections.csv), [optimized connections](../model/results/optimized_connections.csv), and [saved enumeration results](../model/results/enumeration_results.json).

## 5. Step four: formulating the optimization model

### 5.1 The planner's interpretation

#### “What are the six main decisions? How is waiting calculated from them?”

There is one departure-shift decision for each of the six selected trips. Let $x_j$ denote a trip's change in minutes: negative means earlier, positive means later, and zero means unchanged.

For example, for the original 18:20 trip, $x_j=+2$ produces a new departure at 18:22. Its entire trip also moves two minutes later.

For any proposed timetable $x$, we calculate waiting by finding the earliest catchable onward departure:

$$
D_j(x)=d_j+x_j,
\qquad
w_i(x)=\min_{j\in J:\,D_j(x)\ge r_i}\bigl(D_j(x)-r_i\bigr).
$$

Read this as: calculate each new departure $D_j$; keep departures at or after readiness; choose the smallest waiting time. Fixed departures use $x_j=0$.

The planning problem is:

$$
\min_{x\text{ satisfying all rules}}\frac{1}{41}\sum_{i=1}^{41}w_i(x).
$$

We minimize the average, not the maximum individual wait. The maximum is reported as an additional outcome.

#### “What are fixed and nonfixed departures in our analysis?”

The six selected Route 215 departures are adjustable. The other 31 eligible onward departures, including **15:50 and 19:20**, are fixed. Incoming Route 22/23 trips and surrounding vehicle assignments on other routes are also fixed.

An adjustable trip can still receive a zero shift at the optimum. That happens to 16:50 and 18:52. They are unchanged **by the model's choice**, whereas 15:50 and 19:20 must remain unchanged by the problem's definition.

### 5.2 The exact model: sets, choices, and allowed shifts

#### Finite-grid mixed-integer linear formulation

The complete model is collected below so you can see the objective, decision variables, and constraints together. It is the same nominal Scope A formulation as in the [mathematical formulation document](../model/docs/Scope_A_Mathematical_Formulation_2026-11-21.md), expressed in **minutes throughout** to match this guide.

**Unit convention:** $a_i$, $d_j$, and $r_i$ are times measured in **minutes after service-day midnight**. Waiting costs $c_{ijk}$, vehicle gaps $g_{pq}$, minimum gaps $m_{pq}$, headways $h_{e\ell}$, shifts $x_j$, and shift options $k$ are all in **minutes**. The assignment weights $y_{ijk}$ and binary switches $z_{jk}$ are dimensionless. Thus the transfer allowance is **3**, the headway tolerance is **5**, and the objective is average waiting in **minutes**. No factor of 60 is needed in this minute-based formulation.

Before solving, calculate the passenger readiness times, the catchable connection options, and their waiting costs:

$$
\begin{aligned}
r_i&=a_i+3, &&i\in I,\\
F_i&=\{(j,k):j\in J,\ k\in K_j,\ d_j+k\ge r_i\}, &&i\in I,\\
c_{ijk}&=d_j+k-r_i, &&i\in I,\ (j,k)\in F_i.
\end{aligned}
$$

Here $F_i$ lists the departure-and-shift options that opportunity $i$ could catch, and $c_{ijk}$ is the corresponding nonnegative waiting time. Fixed onward departures have $K_j=\{0\}$. A potential connection to an adjustable trip becomes available only when its corresponding shift is selected.

The variables are:

| Variable | Meaning and domain |
|---|---|
| $z_{jk}$ | Binary: one if adjustable trip $j$ uses shift $k$, zero otherwise |
| $x_j$ | Resulting trip shift in minutes, determined by the selected $z_{jk}$; zero for fixed trips |
| $y_{ijk}$ | Continuous, nonnegative assignment weight from opportunity $i$ to connection option $(j,k)\in F_i$ |

Using $|I|=41$, define the MILP:

$$
\begin{aligned}
\min\quad
&\frac{1}{|I|}\sum_{i\in I}\sum_{(j,k)\in F_i}c_{ijk}y_{ijk}\\[4pt]
\text{s.t.}\quad
&\sum_{(j,k)\in F_i}y_{ijk}=1,
&&\forall i\in I,\\[3pt]
&y_{ijk}\le z_{jk},
&&\forall i\in I,\ (j,k)\in F_i,\ j\in A,\\[3pt]
&g_{pq}+x_q-x_p\ge m_{pq},
&&\forall(p,q)\in L,\\[3pt]
&h_{e\ell}-5\le h_{e\ell}+x_\ell-x_e\le h_{e\ell}+5,
&&\forall(e,\ell)\in H,\\[3pt]
&\sum_{k\in K_j}z_{jk}=1,
&&\forall j\in A,\\[3pt]
&x_j=\sum_{k\in K_j}kz_{jk},
&&\forall j\in A,\\[3pt]
&x_j=0,
&&\forall\text{ modeled trips }j\notin A,\\[3pt]
&z_{jk}\in\{0,1\},
&&\forall j\in A,\ k\in K_j,\\[3pt]
&y_{ijk}\ge0,
&&\forall i\in I,\ (j,k)\in F_i.
\end{aligned}
$$

Read the formulation from top to bottom:

| Part | What it requires |
|---|---|
| Objective | Minimize average waiting over all 41 incoming opportunities |
| Full assignment | Each opportunity receives one full unit of assignment across catchable options; fractional weights are permitted |
| Link assignment to a selected shift | An opportunity cannot use a departure option whose binary switch is zero |
| Vehicle availability | Each same-block trip pair retains at least its required turnaround/repositioning allowance |
| Headway bounds | Each affected departure gap stays within five minutes of its original value |
| One shift per selected trip | Exactly one allowed departure option is selected for each of the six adjustable trips |
| Resulting shift | Calculate $x_j$ from the selected option |
| Fixed trips | Every modeled trip outside $A$ keeps its original times, including fixed predecessors/successors on other routes |
| Variable domains | Departure switches are binary; connection weights are continuous and nonnegative |

The whole-trip rule accompanies this formulation: add $x_j$ to every arrival and departure time along selected trip $j$. It is applied when constructing the output timetable, so running and dwell durations remain unchanged and the vehicle-gap equations use the consistently shifted trip endpoints.

**Why is this a finite-grid linear model?** Each $K_j$ is a finite menu of whole-minute shifts. Each catchable option and its waiting cost are computed in advance, so $c_{ijk}$ is a constant multiplying $y_{ijk}$. There is no multiplication of two decision variables, and no Big-M constant is needed to represent catchability. The binary $z$ variables make the formulation mixed-integer; they also force each derived $x_j$ to be one of its allowed whole-minute values.

Continuous $y$ variables are sufficient here because, for a fixed timetable and without capacity restrictions, assigning each opportunity entirely to a minimum-cost available connection is optimal. Fractional optimal assignments can occur when costs tie. Section 5.4 explains this with the 18:20 and 18:22 readiness examples; Section 5.5 works through each constraint numerically.

#### Symbols and units used in the formulation

| Symbol | Meaning in this study | Unit or type |
|---|---|---|
| $I$ | The 41 incoming opportunities | Set of incoming trips |
| $J$ | The 37 eligible onward Route 215 departures | Set of onward trips |
| $A\subset J$ | The six adjustable departures | Set of selected trips |
| $K_j$ | The menu of allowed shifts for departure $j$ | Set of whole-minute shift values |
| $L$ | The 12 relevant pairs of consecutive trips in the same scheduled vehicle block | Set of trip pairs |
| $H$ | The seven affected pairs of consecutive onward Route 215 departures | Set of departure pairs |
| $a_i$ | Incoming scheduled arrival for opportunity $i$; 41 indexed values | Minutes after service-day midnight |
| $d_j$ | Original scheduled onward departure | Minutes after service-day midnight |
| $r_i=a_i+3$ | Passenger readiness | Minutes after service-day midnight |
| $g_{pq}$ | Original scheduled gap between the end of trip $p$ and start of trip $q$ | Minutes |
| $m_{pq}$ | Assumed minimum vehicle gap required for that pair | Minutes |
| $h_{e\ell}$ | Original headway between earlier departure $e$ and later departure $\ell$ | Minutes |
| $k$ | A candidate shift from $K_j$ | Minutes |
| $x_j$ | Resulting shift for trip $j$ | Minutes |
| $F_i$ | Catchable departure-and-shift options for opportunity $i$ | Set of pairs $(j,k)$ |
| $c_{ijk}$ | Waiting cost for opportunity $i$ using option $(j,k)$ | Minutes |
| $z_{jk}$ | Whether shift $k$ is selected for adjustable trip $j$ | Dimensionless binary value |
| $y_{ijk}$ | Opportunity $i$'s assignment weight on option $(j,k)$ | Dimensionless continuous weight |

For example, 16:05 is $16\times60+5=965$ minutes after midnight. A three-minute transfer allowance gives readiness at $965+3=968$, or 16:08. The multiplication by 60 here converts **clock hours to minutes**; the resulting time values used in the model are all minutes.

**How this relates to the original code:** the source inputs store timetable times and gaps in seconds, while departure shifts are already in minutes. Divide the second-valued input fields by 60 before using them in the equations above; do not divide the minute-valued shifts. The original implementation instead converts shifts to seconds internally and converts the resulting objective back to minutes. These are equivalent representations of the same model. This guide consistently uses the minute-based version.

#### “What exactly are the 12 pairs in $L$?”

Each selected trip has an immediately preceding job and an immediately following job in its scheduled block. A pair “touches” a selected trip when the selected trip is either the first or second member. There are six before-links and six after-links, giving 12 distinct pairs.

In the table, “end” refers to the first trip's terminal arrival, and “start” to the next trip's initial departure. All times are the **original schedule**. “QC” means Quincy Center.

| Pair | Selected departure / block | First trip's end → next trip's start | Original gap $g_{pq}$ | Minimum $m_{pq}$ |
|---:|---|---|---:|---:|
| 1 | 16:20 / Q215-56 | R215 ends Ashmont **16:15** → selected R215 starts Ashmont **16:20** | 5 min | 3 min |
| 2 | 16:20 / Q215-56 | Selected R215 ends QC Berth 3 **17:08** → R220 starts QC Berth 4 **17:14** | 6 min | 5 min |
| 3 | 16:50 / Q215-58 | R215 ends Ashmont **16:45** → selected R215 starts Ashmont **16:50** | 5 min | 3 min |
| 4 | 16:50 / Q215-58 | Selected R215 ends QC Berth 3 **17:38** → R225 starts QC Berth 1 **17:56** | 18 min | 5 min |
| 5 | 17:20 / Q238-148 | R215 ends Ashmont **17:15** → selected R215 starts Ashmont **17:20** | 5 min | 3 min |
| 6 | 17:20 / Q238-148 | Selected R215 ends QC Berth 3 **18:05** → R216 starts QC Berth 2 **18:14** | 9 min | 5 min |
| 7 | 17:50 / Q215-54 | R215 ends Ashmont **17:45** → selected R215 starts Ashmont **17:50** | 5 min | 3 min |
| 8 | 17:50 / Q215-54 | Selected R215 ends QC Berth 3 **18:29** → R225 starts QC Berth 1 **18:45** | 16 min | 5 min |
| 9 | 18:20 / Q215-55 | R215 ends Ashmont **18:15** → selected R215 starts Ashmont **18:20** | 5 min | 3 min |
| 10 | 18:20 / Q215-55 | Selected R215 ends QC Berth 3 **18:57** → R215 starts QC Berth 3 **19:05** | 8 min | 3 min |
| 11 | 18:52 / Q215-57 | R215 ends Ashmont **18:45** → selected R215 starts Ashmont **18:52** | 7 min | 3 min |
| 12 | 18:52 / Q215-57 | Selected R215 ends QC Berth 3 **19:29** → R215 starts QC Berth 3 **19:35** | 6 min | 3 min |

These are vehicle-sequence pairs, not passenger connections and not necessarily different routes. Eight pairs are Route 215 followed by Route 215; four involve a following service on another route. The full trip identifiers and endpoint records are in [vehicle_links.csv](../model/inputs/vehicle_links.csv) and [block_trip_endpoints.csv](../model/inputs/block_trip_endpoints.csv).

#### “Does $g_{pq}$ exist because Route 215's bus is needed for another route?”

That is one example, but the broader reason is that **the same scheduled vehicle has successive jobs**. Even if both jobs are Route 215, the vehicle must finish the first before starting the second.

$g_{pq}$ is the gap already present in the schedule. It is not the required buffer: that is $m_{pq}$. For pair 2, the original gap is six minutes and the modeled minimum is five minutes. Only one minute of that gap can be consumed by delaying the selected trip while the following departure remains fixed.

#### “How is $K_j$ calculated? What are the preceding trip and next assignment?”

Start with all whole-minute changes from −5 to +5. Then remove shifts that would prevent the same vehicle from completing its preceding or following job.

For the **16:20 trip**, its preceding job ends at **Ashmont at 16:15**. Allowing three minutes before starting the selected trip gives an earliest departure of **16:18**. It cannot move earlier than −2 minutes.

Its selected journey takes 48 minutes to **Quincy Center Berth 3**. Its next assignment is Route 220, leaving **Quincy Center Berth 4 at 17:14**. The vehicle needs a five-minute gap: three minutes turnaround plus two minutes for the different berth. Therefore it must finish the selected trip by **17:09**, which means departing Ashmont by **16:21**. It cannot move later than +1 minute.

The resulting menu is:

$$
K_{16{:}20}=\{-2,-1,0,+1\}.
$$

| Chosen shift | Ashmont departure | Quincy arrival | Gap after preceding trip | Gap before following assignment |
|---:|---|---|---:|---:|
| −2 | 16:18 | 17:06 | 3 min | 8 min |
| −1 | 16:19 | 17:07 | 4 min | 7 min |
| 0 | 16:20 | 17:08 | 5 min | 6 min |
| +1 | 16:21 | 17:09 | 6 min | 5 min |

Departing at 16:17 would leave only two minutes after the preceding trip, below the required three. Departing at 16:22 would arrive at 17:10, leaving only four minutes before Route 220, below the required five.

With fixed neighboring assignments, the general calculation is:

$$
\begin{aligned}
\text{lower}_j&=\max(-5,\ m_{\text{before}}-g_{\text{before}}),\\
\text{upper}_j&=\min(+5,\ g_{\text{after}}-m_{\text{after}}),\\
K_j&=\{k\in\mathbb Z:\ \text{lower}_j\le k\le\text{upper}_j\}.
\end{aligned}
$$

Applying those calculations gives:

| Original departure | Allowed integer shifts $K_j$ | Possible departure times |
|---|---|---|
| 16:20 | −2, −1, 0, +1 | 16:18–16:21 |
| 16:50 | Every integer from −2 to +5 | 16:48–16:55 |
| 17:20 | Every integer from −2 to +4 | 17:18–17:24 |
| 17:50 | Every integer from −2 to +5 | 17:48–17:55 |
| 18:20 | Every integer from −2 to +5 | 18:18–18:25 |
| 18:52 | Every integer from −4 to +3 | 18:48–18:55 |

For a fixed departure, $K_j=\{0\}$. The menus account for the individual vehicle limits. The headway constraints must still check whether shifts selected from different menus work together.

#### “What are $z_{jk}$ and the resulting shift $x_j$?”

$z_{jk}$ is a binary switch: it equals one if trip $j$ uses shift $k$, and zero otherwise. Exactly one switch for each adjustable trip must be on:

$$
\sum_{k\in K_j}z_{jk}=1,\qquad z_{jk}\in\{0,1\}.
$$

The shift is then calculated from the selected switch:

$$
x_j=\sum_{k\in K_j}kz_{jk}.
$$

For the 16:20 trip, choose $z_{j,-2}=1$ and set the other three switches to zero. Then:

$$
x_j=(-2)(1)+(-1)(0)+(0)(0)+(1)(0)=-2.
$$

The new departure is 16:18. We are choosing one timetable option, not averaging several departure times.

#### “Why isn't each $K_j$ written as a separate constraint?”

It is already enforced by the variables' indexing. We create switches **only for shifts in $K_j$**. For the 16:20 trip there is no switch for +2 or −3. Selecting exactly one existing switch forces $x_j$ to equal an allowed value.

Writing an additional condition $x_j\in K_j$ would repeat the same restriction. The vehicle constraints are also retained explicitly, making the operating logic visible and auditable. In this specific instance, the fixed neighboring assignments mean the correctly derived menus already capture those individual vehicle bounds.

### 5.3 Catchable connections and waiting costs

#### “What does $d_j+k$ mean, and how do we decide whether passengers miss the bus?”

$d_j$ is the original departure and $k$ is the proposed shift, so $d_j+k$ is the departure time under that option. Compare it with readiness $r_i$.

If $d_j+k<r_i$, the bus departs before the passenger group is ready; the connection is excluded. If $d_j+k\ge r_i$, the connection is catchable under the model. Its cost is the resulting wait:

$$
F_i=\{(j,k):j\in J,\ k\in K_j,\ d_j+k\ge r_i\},
\qquad c_{ijk}=d_j+k-r_i.
$$

$F_i$ is simply the list of catchable trip-and-shift options for opportunity $i$. “Cost” here means **minutes of waiting**, not money.

For readiness at 18:22:

| Departure option | Catchable? | Waiting cost |
|---|---|---:|
| Original 18:20 trip with $k=0$: departs 18:20 | No | Excluded; no negative waiting benefit |
| Same trip with $k=+2$: departs 18:22 | Yes | 0 min |
| Same trip with $k=+3$: departs 18:23 | Yes | 1 min |
| Original 18:52 trip with $k=0$: departs 18:52 | Yes | 30 min |

These are potential connections. Only the shift actually chosen for a trip can be used; the assignment constraint below enforces that.

#### “What does $y_{ijk}$ represent? Can you give an example?”

$y_{ijk}$ is the assignment weight linking incoming opportunity $i$ to onward trip $j$ with shift $k$.

For a concrete example, let $i$ be the Route 23 trip arriving at 18:19, and $j$ the Route 215 trip originally departing at 18:20. Then **$y_{i,j,+2}=1$** means: assign this opportunity to that Route 215 trip departing at 18:22 after its +2-minute shift. The corresponding waiting cost is zero.

A value of zero means that connection receives none of the assignment. A value of 0.5 means half of the mathematical assignment weight. It is not a prediction of half a passenger, a passenger count, or a probability that a bus runs.

### 5.4 The objective function and why $y$ can be continuous

The implemented objective is:

$$
\min\ \frac{1}{41}\sum_{i\in I}\sum_{(j,k)\in F_i}c_{ijk}y_{ijk}.
$$

Multiply each possible connection's waiting cost by its assignment weight, add those contributions, and average over the 41 opportunities. A connection receiving weight zero contributes zero. A chosen connection receiving weight one contributes its full waiting time.

#### “I still don't understand why $y$ isn't binary.”

First, hold a feasible timetable fixed just to understand the assignment part. Suppose two available departures are **A at 18:22** and **B at 18:52**, and this opportunity is ready at 18:22.

The assignment weights must be nonnegative and add to one. The following possibilities are mathematically allowed:

| Assignment | Weight on A | Weight on B | Waiting contribution |
|---|---:|---:|---:|
| Everything to A | 1 | 0 | $1(0)+0(30)=0$ min |
| Split equally | 0.5 | 0.5 | $0.5(0)+0.5(30)=15$ min |
| Everything to B | 0 | 1 | $0(0)+1(30)=30$ min |

Because the model minimizes waiting, it prefers the first row. Allowing a fractional assignment does not produce an advantage over assigning everything to the cheapest available connection.

The important point is that **“weights add to one” does not itself mean “exactly one weight is one.”** Fractional values are allowed. The objective makes an all-on-the-cheapest-connection assignment optimal in this model.

#### “What if passenger readiness is 18:20 instead?”

Keep the same example timetable: A departs at 18:22 and B at 18:52. Change only readiness to 18:20. This is a hypothetical readiness example, separate from the actual 18:19 arrival with its three-minute allowance.

| Assignment | Waiting calculation |
|---|---:|
| Everything to A | $1(2)+0(32)=2$ min |
| Half to each | $0.5(2)+0.5(32)=17$ min |
| Everything to B | $0(2)+1(32)=32$ min |

The model still assigns everything to A. **The cheapest connection does not need to have zero wait.** It only needs to be cheaper than the alternatives. The earlier $0.5(0)+0.5(30)=15$ calculation applies to readiness at 18:22; after changing readiness to 18:20, the corresponding split costs 17 minutes.

If the timetable itself is also allowed to change, the optimizer may reconsider the departure shift. These examples hold it fixed to explain why fractional assignment offers no improvement. The actual optimization chooses timetable and assignment variables together.

#### “Does that guarantee every $y$ is always zero or one?”

No. If two available connections have the same minimum cost, a split between them can also be optimal. For example, two connections both costing two minutes yield two minutes whether the weights are 1/0 or 0.5/0.5.

The precise claim is: **an optimal all-or-nothing assignment exists for any fixed feasible timetable**, because each opportunity can independently use a lowest-cost available connection. It is not necessary to require binary $y$ to obtain the correct minimum waiting value. A weighted average of available costs cannot be lower than the smallest cost.

This argument relies on the current model having no capacity limits or other constraints coupling different opportunities' assignments. If those are added, we must review the assignment formulation. Making $y$ binary now would be valid but would add unnecessary integer restrictions.

#### “How does that produce the reference objective value of 12.4634?”

Evaluate every opportunity under the optimal timetable. The 18:19 arrival contributes zero waiting, the 17:52 arrival contributes 27 minutes, and the other 39 contribute their respective waits. The complete saved sum is **511 minutes**, split as 225 for Route 22 opportunities and 286 for Route 23 opportunities:

$$
\text{Optimized objective}=\frac{225+286}{41}=\frac{511}{41}=12.4634146\ldots\text{ minutes}.
$$

This value uses all 41 rows, not just the illustrative connection with a 30-minute improvement.

### 5.5 Each constraint, with a worked example

#### A. Select exactly one shift for every adjustable departure

$$
\sum_{k\in K_j}z_{jk}=1,\qquad z_{jk}\in\{0,1\}.
$$

For the 16:20 trip, one of −2, −1, 0, or +1 must be selected. Choosing both −2 and +1 would make the sum two and is forbidden. Choosing none would make the sum zero and is also forbidden. Fixed trips have $x_j=0$.

#### B. Fully assign every opportunity, and use only a chosen departure option

$$
\sum_{(j,k)\in F_i}y_{ijk}=1,\qquad y_{ijk}\ge0.
$$

This requires one full unit of assignment across catchable options. It prevents the optimizer from obtaining zero cost by simply omitting an inconvenient opportunity.

For adjustable trips, also impose:

$$
y_{ijk}\le z_{jk}.
$$

If the 18:20 trip is kept unchanged, then $z_{j,+2}=0$, forcing $y_{i,j,+2}=0$. Passengers ready at 18:22 cannot pretend that a nonexistent 18:22 departure is available. If the +2 shift is selected, $z_{j,+2}=1$ and that connection may receive assignment. Nonadjustable trips have their fixed $k=0$ option available without a departure-choice switch.

#### C. Preserve vehicle availability

Let trip $p$ originally end at $E_p$ and its same-block successor $q$ originally start at $S_q$. Their original gap is $g_{pq}=S_q-E_p$. After shifting the trips, the remaining gap must still cover the required allowance:

$$
(S_q+x_q)-(E_p+x_p)\ge m_{pq}.
$$

Rearrange the terms:

$$
g_{pq}+x_q-x_p\ge m_{pq}.
$$

Moving the later job later increases the gap; moving the earlier job later consumes the gap. The letters $p$ and $q$ identify trips, not routes.

For the selected 16:20 trip, let its shift be $x$. Its preceding trip is fixed, so the before-link gives:

$$
5+x-0\ge3\quad\Longrightarrow\quad x\ge-2.
$$

Its following Route 220 departure is fixed, so the after-link gives:

$$
6+0-x\ge5\quad\Longrightarrow\quad x\le1.
$$

These are exactly the limits used to derive $K_{16{:}20}$. Shifting by −2 satisfies both: the before-gap is three minutes and the after-gap is eight. Shifting by +2 fails the after-link: only four minutes remain.

#### D. Keep affected headways within five minutes of their original values

**“What is a consecutive departure? What are the seven pairs in $H$?”**

Consecutive departures are adjacent departures in the ordered timetable for the same service and direction. In this model, they are **Route 215 departures from Ashmont toward Quincy**. They need not use the same physical vehicle.

This is different from $L$, which follows one vehicle through successive jobs. It is also different from $A$: $A$ contains six individual adjustable trips, whereas $H$ contains seven pairs.

The six adjustable departures, plus the fixed immediate neighbors 15:50 and 19:20, form eight departures and therefore seven adjacent gaps:

| Pair in $H$ | Earlier departure → later departure | Original headway | Allowed new headway |
|---:|---|---:|---:|
| 1 | **15:50 fixed** → 16:20 | 30 min | 25–35 min |
| 2 | 16:20 → 16:50 | 30 min | 25–35 min |
| 3 | 16:50 → 17:20 | 30 min | 25–35 min |
| 4 | 17:20 → 17:50 | 30 min | 25–35 min |
| 5 | 17:50 → 18:20 | 30 min | 25–35 min |
| 6 | 18:20 → 18:52 | 32 min | 27–37 min |
| 7 | 18:52 → **19:20 fixed** | 28 min | 23–33 min |

The fixed neighbors matter because shifting the first or last adjustable departure changes its gap with service just outside the decision window. Without those two boundary checks, the model would ignore an affected service interval.

For earlier departure $e$ and later departure $\ell$, the constraint is:

$$
h_{e\ell}-5
\le (d_\ell+x_\ell)-(d_e+x_e)
\le h_{e\ell}+5.
$$

Since $h_{e\ell}=d_\ell-d_e$, this is equivalent to:

$$
-5\le x_\ell-x_e\le5.
$$

Your interpretation was essentially right: subtract the **new earlier departure** from the **new later departure**, and require the gap to lie between the original headway minus five and the original headway plus five. Both a lower and an upper bound apply.

Worked example: move 17:50 by −1 to 17:49 and 18:20 by +2 to 18:22. The new gap is **33 minutes**, within 25–35. Equivalently, the gap changes by $+2-(-1)=+3$ minutes.

A counterexample shows why $K_j$ alone is insufficient: shifting 17:50 by −2 and 18:20 by +5 is individually allowed by their vehicle menus, but creates a gap from **17:48 to 18:25**, or 37 minutes. That exceeds the 35-minute headway limit and is forbidden.

At the left boundary, moving 16:20 to 16:18 leaves 28 minutes after the fixed 15:50 departure, which is allowed. At the right boundary, moving 18:52 to 18:55 leaves 25 minutes before fixed 19:20, also allowed for that boundary pair.

#### E. Shift each selected trip as a whole

For every stop on a selected trip:

$$
\text{new stop time}=\text{original stop time}+x_j.
$$

Both arrival and departure times move by the same amount. For example, the 16:20–17:08 trip with $x_j=-2$ becomes **16:18–17:06**, still taking 48 scheduled minutes. All intermediate stop times also move two minutes earlier, preserving the scheduled running and dwell intervals.

This rule is applied when constructing the output timetable; the model does not independently choose a different shift at every stop. Without whole-trip movement, departing earlier while leaving the final arrival unchanged would quietly change the assumed trip duration.

### 5.6 Why there is no active stranded-transfer penalty

The latest readiness among these 41 nominal opportunities is **18:58**, and the fixed 19:20 departure remains available. Every opportunity therefore has at least one catchable departure for every permitted timetable.

The nominal objective contains no stranded-transfer penalty. A 60-minute penalty was retained as a possible convention for future cases with genuinely no onward service; it is not used to generate the current results. Such an extension must not let the model voluntarily label someone stranded merely to avoid a larger real wait.

For the complete compact formulation, see the [readable mathematical formulation](../model/docs/Scope_A_Mathematical_Formulation_2026-11-21.md). Its historical “next steps” should be read alongside the later status in Section 9 here.

## 6. Step five: solving the model and checking the result

### “Where did 12.46 minutes and 7.76% come from? Was optimization actually used?”

Yes. Two executed methods found the same optimum:

| Method | What it does | Recorded outcome |
|---|---|---|
| Exhaustive enumeration in Python | Tries combinations of allowed shifts, rejects those violating the rules, and evaluates all 41 waits for every feasible timetable | **71,673 feasible timetables**; one unique best shift vector |
| SciPy/HiGHS MILP | Solves the mathematical optimization formulation using binary timetable choices and continuous connection assignments | Same shift vector and objective; solver-reported zero optimality gap |

Enumeration is itself an exact optimization method for a finite search space: it finds the best candidate by checking every feasible candidate. The MILP is a separate computational implementation of the optimization problem. Agreement checks both the model's formulation and its resulting timetable more convincingly than one implementation alone.

The November 6 package records these results. The November 19 work reran the calculations and reproduced them. The guide you are reading explains those records; creating this document did not rerun either solver.

### “But it was SciPy/HiGHS, not Gurobi/Julia?”

These names describe different layers:

| Name | Role | Project use |
|---|---|---|
| Python | Programming language | Executed enumeration, SciPy model, and later experiments |
| SciPy | Python scientific-computing library, including an optimization interface | Used to submit the MILP to HiGHS |
| Julia | Programming language | Separate implementation supplied but execution still pending in the package record |
| JuMP | Optimization modeling package in Julia | Used to express the Julia version of the model |
| HiGHS | Optimization solver | Solved the Python MILP; also specified for the supplied Julia implementation |
| Gurobi | Another optimization solver | No Gurobi execution is claimed in the saved work |

A calculation does not need to use Gurobi or Julia to count as optimization. The outstanding Julia task is to verify that the supplied **Julia/JuMP/HiGHS implementation** reproduces the established result.

### “What timetable did the optimizer choose?”

In the original chronological order of the six selected departures:

$$
x=(-2,0,-2,-1,+2,0)\text{ minutes}.
$$

| Original departure | Shift | Optimized departure |
|---|---:|---|
| 16:20 | −2 min | **16:18** |
| 16:50 | 0 min | 16:50 |
| 17:20 | −2 min | **17:18** |
| 17:50 | −1 min | **17:49** |
| 18:20 | +2 min | **18:22** |
| 18:52 | 0 min | 18:52 |

Six trips are adjustable, but only four are changed in the selected optimum.

### “Can you show the improvement calculation?”

The total waiting decreases from 554 to 511 opportunity-minutes, a net reduction of 43:

$$
\begin{aligned}
\text{Mean reduction}&=\frac{554-511}{41}=1.0487805\ldots\text{ minutes},\\
\text{Percentage reduction}&=\frac{554-511}{554}\times100=7.7617329\ldots\%.
\end{aligned}
$$

The displayed figures 13.51, 12.46, 1.05, and 7.76% are rounded. Calculate the percentage from the unrounded values, rather than subtracting the rounded displayed averages.

| Measure | Original schedule | Optimal nominal schedule |
|---|---:|---:|
| Total opportunity-weighted waiting | 554 min | 511 min |
| Average waiting after allowance | 13.5122 min | **12.4634 min** |
| Average arrival-to-departure transfer time | 16.5122 min | **15.4634 min** |
| Maximum waiting after allowance | 30 min | **27 min** |
| Opportunities waiting at most ten minutes | 15/41 | **20/41** |
| Stranded opportunities | 0 | 0 |

### “Does everyone benefit?”

No. Waiting decreases for **18 opportunities**, increases for **seven**, and stays unchanged for **16**. Each worsened opportunity waits two minutes more.

The 18:19 arrival's 30-minute saving accounts for 30 of the 43 net minutes saved. That concentration matters: without passenger counts, we do not know how many people benefit from that particular connection relative to the groups that wait longer.

The model also does not quantify every effect on other Route 215 riders, crew arrangements, or the rest of the network. Preserving vehicle feasibility is necessary, but it is not a complete assessment of operational or passenger impacts.

### “What does ‘optimal’ prove?”

It proves that no timetable in the **specified whole-minute search space**, satisfying the adopted vehicle and headway rules, achieves a lower value of this objective. Enumeration found a unique best vector in that space, and the MILP independently agreed.

It does not establish the best possible schedule over unrestricted continuous departure times, different passenger weights, other service days, altered routes, or actual delayed operations. A zero solver gap establishes completion of the specified mathematical problem, not correctness of every real-world assumption.

Sources: [enumeration record](../model/results/enumeration_results.json), [SciPy/HiGHS record](../model/results/scipy_milp_crosscheck.json), and [recommended shifts](../model/results/recommended_departure_shifts.csv).

## 7. Step six: implementation and validation work

### “What has been implemented and checked?”

The project contains data-preparation outputs, a written formulation, the original Python enumeration and MILP implementations, the supplied Julia/JuMP implementation, and saved results. The later package adds reviewed Julia source, a Python experiment engine, expanded validation, and figures.

The nominal MILP contains **43 binary departure-option variables**, **1,386 continuous connection-assignment variables**, and **1,042 linear constraints**. The six planner decisions become 43 possible binary menu options; this is why “six decisions” does not mean “only six variables in the solver.”

The November 19 verification checked several distinct questions:

| Check | What it supports |
|---|---|
| Reconstruct eight inputs from the adopted historical archive | The saved scheduled inputs are reproducible |
| Rerun enumeration and SciPy/HiGHS | The nominal objective and shift vector reproduce |
| Independently recalculate earliest catchable departures | Reported waits correspond to actual available timetable choices |
| Audit all 300 selected stop-time rows | Whole trips move consistently, without changing scheduled running/dwell durations |
| Check all 33 consecutive pairs across affected blocks | No trip overlap is introduced across those blocks |
| Check minimum allowances on the 12 links touching selected trips | Those affected vehicle links meet the adopted buffer rules |
| Run original and new tests | Documented computational behaviors pass the recorded checks |

The other 21 unchanged block links were checked for nonnegative gaps; this does not certify them against undocumented MBTA operating-buffer policies. The recorded test runs passed **12 original tests and 34 new tests**, alongside an independent check of **5,740 opportunity/case/timetable rows**.

### “What happened to the November 12 code patch?”

The November 12 revision included code-review notes and a patch. The November 19 package **applied the patch to a separate reviewed Julia source file**, retaining the original.

The reviewed version preserves timetable clock fields as strings and improves solution-status handling, including distinguishing a feasible result obtained before a time limit from a proven optimum. It also records outputs needed for comparison. These are reviewed source changes, not proof of a successful Julia execution.

Relevant files are [original Julia source](../model/src/run_scope_a.jl), [reviewed Julia source](../model/src/run_scope_a_reviewed.jl), and [Julia execution status](../validation/julia_execution_status.json).

### “What exactly remains to be done for Julia?”

Run the reviewed code with the frozen nominal inputs, preserve the actual solver and environment records, and compare the outputs with the independent reference. The recorded authoring environment could not obtain a working Julia runtime, so the package does not claim that run has occurred.

The expected result is the shift vector **(−2, 0, −2, −1, +2, 0)** with mean waiting **12.4634 minutes**. Verification should also check the selected connections, full-trip shifts, vehicle gaps, headways, solver termination status, and objective bound/gap. Matching one number alone is insufficient.

The package supplies a [Windows launcher](../model/src/setup_and_run_reviewed.ps1), a [shell launcher](../model/src/setup_and_run_reviewed.sh), and an [output verifier](../validation/verify_julia_outputs.py). A real run should retain the generated dependency Manifest, versions, console log, solver summary, and CSV outputs. A discrepancy should be investigated, not hidden by inserting the expected shift vector into the code.

## 8. Step seven: what we did for the interim report

### “What did we produce, and which version is the latest interim?”

The original November 6 materials included the formulation, preliminary computational evidence, and an interim-report draft. The later revision produced the **November 12 version 2 one-page interim report**, available in Markdown, Word, and PDF in `latest_interim/`.

The report revision improved the explanation and presentation of the existing study. It was not a new optimization experiment and did not replace the nominal results with a different solution.

Read the [November 12 interim report](../latest_interim/MBTA_Interim_Report_v2_2026-11-12.md) for the concise deliverable. The project records establish that it was prepared; they do not by themselves establish its submission to the course.

### “What does that report actually say?”

It presents the project in this sequence:

1. **Problem:** improve transfers from Routes 22/23 to Route 215 by retiming six departures on one scheduled service day.
2. **Data:** 41 equal-weight opportunities and all 37 eligible onward departures, with historical timetable reconciliation.
3. **Method:** a deterministic MILP, whole-minute shifts, whole-trip movement, vehicle availability, and headway restrictions.
4. **Assumptions:** three-minute passenger transfer and vehicle turnaround allowances, two additional minutes for a different Quincy berth, and ±5-minute shift/headway limits.
5. **Results:** 13.51 to 12.46 minutes average waiting, or 1.05 minutes and 7.76%; maximum waiting 30 to 27; opportunities within ten minutes 15 to 20.
6. **Specific changes and distribution:** four changed departures, with 18 opportunities improved, seven worsened, and 16 unchanged.
7. **Computational status:** Python enumeration and SciPy/HiGHS agree; Julia/JuMP execution remains pending.
8. **Interpretation and next steps:** a modest scheduled benefit for planner review, followed by Julia verification, a heuristic benchmark, and sensitivity analysis; Scope B deferred.

It explicitly avoids treating equal-weight opportunities as measured passenger counts or presenting the proposed timetable as ready for deployment. Those limitations are part of the result's meaning, not incidental footnotes.

### “Did the November 19 package replace that interim report?”

No. The November 19 package preserves the November 12 report unchanged. It adds verification and experiment findings in separate documents.

This creates an important date distinction: the interim report lists heuristic comparison and sensitivity analysis as **next steps**, because they had not yet been completed at that report's date. The November 19 status records their later completion. Both documents can be accurate about their respective stages.

Similarly, the formulation's original November 6 next-steps list is historical. Use the [November 22 current-status document](CURRENT_STATUS_2026-11-22.md), based on the November 19 computational evidence, to identify outstanding work.

## 9. What remains—and how Scope B fits

This section updates the final section of your pasted outline. Its earlier “pending” labels for benchmarking and sensitivity were superseded by the November 19 work.

### “Are benchmark comparison and sensitivity analysis still part of Scope A?”

Yes. Both can evaluate the same deterministic scheduled-service problem.

**Benchmarking** asks whether a simpler feasible adjustment rule performs as well as the optimizer. This differs from comparing two optimization implementations: enumeration-versus-MILP agreement verifies the answer; heuristic-versus-optimum comparison assesses whether the optimization delivers extra benefit over a simpler approach.

**Sensitivity analysis** asks how the result changes when assumptions such as transfer allowance, turnaround, berth movement, shift cap, or headway tolerance change. It remains Scope A when the tests use deterministic schedules and specified parameter values. It does not automatically become an analysis of real observed delays.

### “What did the later benchmark show?”

The tested simple rule starts at the original timetable and visits the six adjustable departures once, in chronological order. For each trip, it checks feasible shifts while holding the other current choices fixed, accepting a change only if total waiting decreases. Ties between equally good improvements favor smaller absolute changes, then earlier departures. It does not consult the optimizer's answer.

That rule obtained **the same nominal timetable and 12.4634-minute mean wait**. It also matched the optimal objective in all 32 feasible tested cases, including diagnostic cases. Matching objective values does not necessarily mean the timetables are identical in every case.

We therefore cannot claim the MILP outperformed this heuristic in the tested instances. Its contribution includes certifying optimality within the defined model and supporting consistent comparisons. A heuristic matching the optimum on these instances does not guarantee it will match on larger or different problems.

### “What did sensitivity analysis show? Why distinguish reoptimization from a stress test?”

The November 19 suite ran **38 cases: 32 feasible optimal cases and six structurally infeasible cases**. Independent enumeration confirmed 31 feasible optima; the half-minute-grid case was solved and independently evaluated, but was not exhaustively enumerated because its option product exceeded the preset enumeration limit.

There are two different questions when an assumption changes:

| Test | What stays fixed? | Question answered |
|---|---|---|
| Reoptimize under the new assumption | Model structure and relevant data; timetable decisions may change | What is the best timetable for this different assumption? |
| Stress-test the original recommendation | The nominal shift vector stays **(−2, 0, −2, −1, +2, 0)** | Does that same recommendation still perform well? |

For passenger transfer allowance alone:

| Allowance | Original timetable mean wait | Reoptimized mean wait | Unchanged nominal recommendation's mean wait |
|---:|---:|---:|---:|
| 2 min | 14.5122 | 12.7073 | 13.4634 |
| 3 min | 13.5122 | 12.4634 | 12.4634 |
| 5 min | 13.6585 | 11.8537 | **15.6829** |

All values are waiting **after** the allowance. Compare original and optimized timetables within the same row. For arrival-to-departure transfer time, add that row's allowance: for example, the five-minute reoptimized total is 16.8537 minutes, while the three-minute reoptimized total is 15.4634 minutes.

At a five-minute allowance, retiming afresh can improve the schedule, but the unchanged nominal recommendation performs **worse than the original timetable**. Thus, “an improvement exists under another assumption” does not mean “our current recommendation remains good under that assumption.”

Seven nominal optimized connections depend on readiness exactly equaling departure. A diagnostic increase from 180 to 181 seconds raises the unchanged recommendation's mean wait to 17.6663 minutes. This illustrates a catch/miss boundary in the deterministic model; it is not a measured real-world delay forecast.

Two other findings help explain the role of constraints:

- A **±2-minute departure cap** retains the full nominal improvement. A **±2-minute headway tolerance** gives a slightly higher optimum of 12.5122 minutes. These limits constrain different quantities.
- A **five-minute turnaround plus two-minute berth allowance** makes the fixed-neighbor problem infeasible. For the 16:20 trip, the before-link requires $5+x\ge5$, so $x\ge0$. The after-link requires $6-x\ge7$, so $x\le-1$. No shift satisfies both. This is an inconsistency between the stricter requirements and the fixed neighboring schedule, not a failed solver or a missing observation.

Experiments must regenerate the allowed menus and all affected constraints when parameters change. Reusing the old $K_j$ values after changing turnaround assumptions would test the wrong problem.

Full results and limitations are in [Validation and experiment findings](VALIDATION_AND_EXPERIMENT_FINDINGS.md).

### “If the study is too narrow, what could we change?”

| Possible extension | What it would add | What must be reconsidered |
|---|---|---|
| Extend the window to the full day | More arrivals and adjustable departures | Rebuild the cohort, boundaries, vehicle links, and headways |
| Add days or transfer routes | Broader scheduled-service coverage | Define consistent comparisons and new inputs |
| Add passenger weights | A passenger-weighted benefit measure | Obtain credible transfer demand estimates |
| Add capacity or crowding | Represent denied boarding or competition for space | Revise assignment constraints and data requirements |
| Model actual delays / Scope B | Evaluate reliability and uncertainty | Validate event clocks, coverage, scenarios, and vehicle endpoints |
| Change scheduled running times | Study travel-time assumptions or a broader timetable design problem | Justify the changes and update whole-trip timings and vehicle feasibility |

Sensitivity analysis already broadens what we can say about Scope A. A larger scope is not automatically a stronger study; it should address a clear limitation with sufficient evidence.

In particular, arbitrarily increasing trip durations would not make the model more realistic. If we believe scheduled running times are too short, we need evidence and a consistent way to change the trip's stop times and subsequent vehicle availability. Adding trips would likewise require assumptions about vehicles, crews, and resources that the current fixed-trip model does not contain.

### “What would Scope B do?”

Scope B remains a separate, deferred extension. The proposed idea is to choose **one timetable** that performs reasonably across scheduled, representative, and disrupted conditions, after those scenarios have been validated.

One proposed objective is:

$$
\min_{x\text{ feasible}}\ \max_{s\in S}\ \frac{1}{41}\sum_{i=1}^{41}w_{is}(x),
$$

where $S$ is the set of scenarios and $w_{is}(x)$ is opportunity $i$'s waiting under timetable $x$ in scenario $s$.

For each candidate timetable, calculate the average wait in each scenario, take the worst of those averages, then choose the timetable with the lowest worst-case average. It does not choose a different timetable after learning which scenario occurs, and it is not minimizing the single worst passenger's wait.

This formulation describes an intended extension, not an executed result. Historical delay interpretation and missing Quincy vehicle observations still need attention before making delay-based operational claims.

### “What is complete, and what is still unfinished?”

| Component | Status supported by the November 19 package |
|---|---|
| Scheduled data preparation and historical reconciliation | Completed |
| Scope A formulation and nominal baseline | Completed and documented |
| Python enumeration and SciPy/HiGHS optimization | Executed; later reproduced |
| Revised one-page interim report | November 12 v2 prepared and preserved |
| Julia code review and patch application | Reviewed source prepared |
| Actual Julia execution and output verification | **Pending** |
| Feasible heuristic comparison | Completed in Python; tied the optimum in tested feasible cases |
| Sensitivity experiments and validation | Completed in Python, with infeasible cases explicitly identified |
| Consolidated reference package | Completed |
| Scope B | **Deferred** |
| Final technical report, slides, and video | **Not completed in this package** |
| MBTA operational approval or observed passenger-benefit validation | Not established by this study |

### “Which files should I use from now on?”

Use **`MBTA_All_In_One_Validated_ScopeA_2026-11-22/`** as the current working folder. It derives from **`MBTA_All_In_One_Validated_ScopeA_2026-11-19.zip`**, which remains the unchanged reference snapshot. The November 22 revision updates documentation, filenames, and package metadata; the computational evidence still comes from November 19. The reference contains the earlier source archives; their old “pending,” “partial,” or “missing file” statements describe earlier stages.

| Purpose | File or location |
|---|---|
| Plain-language explanation with your questions | This guide |
| Package orientation | [README_FIRST.md](../README_FIRST.md) |
| Latest packaged completion status | [CURRENT_STATUS_2026-11-22.md](CURRENT_STATUS_2026-11-22.md) |
| Latest packaged experiment findings | [VALIDATION_AND_EXPERIMENT_FINDINGS.md](VALIDATION_AND_EXPERIMENT_FINDINGS.md) |
| Original model mathematics with readable delimiters | [Scope_A_Mathematical_Formulation_2026-11-21.md](../model/docs/Scope_A_Mathematical_Formulation_2026-11-21.md) |
| Latest interim report, still November 12 v2 | [Interim report](../latest_interim/MBTA_Interim_Report_v2_2026-11-12.md) |
| Inputs, source code, and original nominal results | `model/` |
| Later experiments and results | `experiments/`, `results/`, and `validation/` |
| Earlier preserved packages | `source_archives/` |

Keep subsequent verified code changes and results in a newly dated release with an explicit record of what supersedes the reference. A complete reference package means the materials are consolidated; it does not mean the unfinished Julia verification or final course deliverables have already been completed.


