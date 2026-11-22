# Scope A: exact one-minute-grid mixed-integer linear timetable model.
# The same date, input tables, and assumed constraints as reference_enumeration.py.
# Requires Julia + CSV.jl, DataFrames.jl, JuMP.jl, HiGHS.jl.
# Run from project root: julia --project=. src/run_scope_a.jl
# No Julia executable was available in the preparation environment; see README.
using CSV
using DataFrames
using JuMP
using HiGHS

const ROOT = normpath(joinpath(@__DIR__, ".."))
const INPUTS = joinpath(ROOT, "inputs")
const OUTPUTS = joinpath(ROOT, "results")
mkpath(OUTPUTS)

as_id(x) = string(x)
function hms(seconds::Integer)
    @assert seconds >= 0
    return lpad(string(seconds ÷ 3600), 2, '0') * ":" *
           lpad(string((seconds % 3600) ÷ 60), 2, '0') * ":" *
           lpad(string(seconds % 60), 2, '0')
end
function parse_hms(x)
    parts = parse.(Int, split(string(x), ":"))
    @assert length(parts) == 3
    return parts[1]*3600 + parts[2]*60 + parts[3]
end

incoming = CSV.read(joinpath(INPUTS, "incoming.csv"), DataFrame; types=Dict(:trip_id=>String, :route_id=>String))
outgoing = CSV.read(joinpath(INPUTS, "outgoing.csv"), DataFrame; types=Dict(:trip_id=>String))
links = CSV.read(joinpath(INPUTS, "vehicle_links.csv"), DataFrame;
    types=Dict(:predecessor_trip_id=>String,:successor_trip_id=>String))
headways = CSV.read(joinpath(INPUTS, "headway_limits.csv"), DataFrame;
    types=Dict(:earlier_trip_id=>String,:later_trip_id=>String))
limits = CSV.read(joinpath(INPUTS, "shift_bounds_checked.csv"), DataFrame)
params = CSV.read(joinpath(INPUTS,"model_parameters.csv"), DataFrame)
parameter = Dict(string(r.parameter)=>parse(Int,string(r.value)) for r in eachrow(params))
@assert parameter["integer_shift_step_seconds"] == 60
τ = parameter["transfer_allowance_seconds"]
penalty = parameter["stranded_penalty_seconds"] # only if truly no onward service
@assert τ == 180 && penalty == 3600
@assert nrow(incoming) == 41 && nrow(outgoing) == 37

sort!(outgoing, :departure_sec)
movable = outgoing[outgoing.is_adjustable .== 1, :]
sort!(movable, :departure_sec)
@assert nrow(movable) == nrow(limits) == 6
@assert [string(x)[1:5] for x in movable.departure_time] == string.(limits.departure)

# One key per eligible outward bus; fixed buses receive only a zero-minute option.
all_ids = string.(outgoing.trip_id)
movable_ids = string.(movable.trip_id)
movable_set = Set(movable_ids)
dep = Dict(string(r.trip_id)=>Int(r.departure_sec) for r in eachrow(outgoing))
allowed = Dict{String,Vector{Int}}()
for (idx,r) in enumerate(eachrow(movable))
    l = limits[idx,:]
    low,high = Int(l.earliest_shift_min),Int(l.latest_shift_min)
    @assert -5 <= low <= 0 <= high <= 5
    allowed[string(r.trip_id)] = collect(low:high)
end
for j in all_ids
    if !(j in movable_set)
        allowed[j] = [0]
    end
end

# Every arrival in the selected fixed cohort has a later fixed 19:20 departure.
# This is checked here, so no stranded alternative is included in this model.
# A future no-service dataset must use a forced (not optional) penalty treatment.
ready = [Int(t)+τ for t in incoming.arrival_sec]
@assert maximum(ready) < 19*3600+20*60
@assert any(dep[j] == 19*3600+20*60 && !(j in movable_set) for j in all_ids)

# For each arrival i, (i,j,k) is allowed iff the trip with shift k is catchable.
# The cost of this arc is known ahead of time: d_j + 60*k - ready_i.
arcs_by_i = Vector{Vector{Tuple{Int,String,Int}}}(undef, nrow(incoming))
arcs = Tuple{Int,String,Int}[]
for i in eachindex(ready)
    arcs_i = Tuple{Int,String,Int}[]
    for j in all_ids, k in allowed[j]
        if dep[j] + 60*k >= ready[i]
            push!(arcs_i, (i,j,k))
        end
    end
    @assert !isempty(arcs_i) "No catchable trip for opportunity $i"
    arcs_by_i[i] = arcs_i
    append!(arcs, arcs_i)
end
choices = [(j,k) for j in movable_ids for k in allowed[j]]

model = Model(HiGHS.Optimizer)
set_time_limit_sec(model, 180.0)
# z(j,k)=1 if the selected Route 215 trip j shifts k whole minutes.
@variable(model, z[c in choices], Bin)
@constraint(model, [j in movable_ids], sum(z[(j,k)] for k in allowed[j]) == 1)
@expression(model, x[j in movable_ids], sum(k*z[(j,k)] for k in allowed[j]))

# Transfer-assignment variables are continuous: conditional on z, the minimum
# objective selects the earliest catchable departure, without Big-M constants.
# There is no capacity constraint and all costs are nonnegative.
@variable(model, y[a in arcs] >= 0)
for i in eachindex(ready)
    @constraint(model, sum(y[a] for a in arcs_by_i[i]) == 1)
end
for a in arcs
    _,j,k = a
    if j in movable_set
        @constraint(model, y[a] <= z[(j,k)])
    end
end

# Preserve the predecessor/successor block-chain buffers at both ends.
# Fixed surrounding trips have a shift of zero.
shift_of(trip_id::String) = trip_id in movable_set ? x[trip_id] : 0
for r in eachrow(links)
    pred, succ = string(r.predecessor_trip_id), string(r.successor_trip_id)
    @constraint(model,
       Int(r.scheduled_gap_sec) + 60*(shift_of(succ)-shift_of(pred)) >= Int(r.minimum_gap_sec))
end

# Every adjacent Route 215 departure within the relevant window, including
# the fixed departure just before and after the six adjusted departures.
for r in eachrow(headways)
    before, after = string(r.earlier_trip_id), string(r.later_trip_id)
    actual_headway = Int(r.scheduled_headway_sec) + 60*(shift_of(after)-shift_of(before))
    @constraint(model, actual_headway >= Int(r.minimum_headway_sec))
    @constraint(model, actual_headway <= Int(r.maximum_headway_sec))
end

# Mean post-allowance waiting minutes over all 41 equal-weight opportunities.
@objective(model, Min,
    (1/length(ready))*sum((dep[j]+60*k-ready[i])/60 * y[(i,j,k)] for (i,j,k) in arcs))

# Baseline check at zero shift, performed directly from the source tables.
function evaluate(shifts::Dict{String,Int})
    actual = [(j,dep[j]+60*get(shifts,j,0)) for j in all_ids]
    sort!(actual, by=t->t[2])
    rows = NamedTuple[]
    for i in eachindex(ready)
        eligible = findfirst(t->t[2]>=ready[i], actual)
        if eligible === nothing
            push!(rows,(opportunity_id=string(incoming.opportunity_id[i]),
                        source_route=string(incoming.route_id[i]),
                        source_trip_id=string(incoming.trip_id[i]),
                        destination_trip_id="",wait_seconds=penalty,served=false))
        else
            j, d = actual[eligible]
            push!(rows,(opportunity_id=string(incoming.opportunity_id[i]),
                        source_route=string(incoming.route_id[i]),
                        source_trip_id=string(incoming.trip_id[i]),
                        destination_trip_id=j,wait_seconds=d-ready[i],served=true))
        end
    end
    return DataFrame(rows)
end
baseline = evaluate(Dict(j=>0 for j in movable_ids))
@assert nrow(baseline)==41
@assert sum(baseline.wait_seconds)==33240
@assert all(baseline.served)
println("BASELINE: mean post-allowance wait = ",sum(baseline.wait_seconds)/41/60," min")

optimize!(model)
println("JuMP termination status: ",termination_status(model))
println("JuMP primal status: ",primal_status(model))
if !has_values(model)
    error("Solver returned no feasible timetable; inspect statuses and constraints")
end
shifts = Dict(j => round(Int,value(x[j])) for j in movable_ids)
result = evaluate(shifts)
mean_wait = sum(result.wait_seconds)/nrow(result)/60
println("Selected 6 trip shifts (minutes): ",[shifts[j] for j in movable_ids])
println("Independently reevaluated mean wait: ",mean_wait, " min")
println("JuMP model objective: ",objective_value(model)," min")
@assert abs(mean_wait-objective_value(model))<1e-5
@assert all(result.served)

# Check constraints independent of solver construction.
for r in eachrow(links)
    actual_gap = Int(r.scheduled_gap_sec) +
       60*(get(shifts,string(r.successor_trip_id),0)-get(shifts,string(r.predecessor_trip_id),0))
    @assert actual_gap>=Int(r.minimum_gap_sec)
end
for r in eachrow(headways)
    actual_gap = Int(r.scheduled_headway_sec) +
       60*(get(shifts,string(r.later_trip_id),0)-get(shifts,string(r.earlier_trip_id),0))
    @assert Int(r.minimum_headway_sec)<=actual_gap<=Int(r.maximum_headway_sec)
end
CSV.write(joinpath(OUTPUTS,"jump_optimized_connections.csv"), result)
summary=DataFrame(trip_id=movable_ids,
                  original_departure=string.(movable.departure_time),
                  shift_minutes=[shifts[j] for j in movable_ids],
                  optimized_departure=[hms(dep[j]+60*shifts[j]) for j in movable_ids])
CSV.write(joinpath(OUTPUTS,"jump_shift_schedule.csv"),summary)

# Write the entire modified stop-time trajectory; no travel time is shortened.
stops=CSV.read(joinpath(INPUTS,"selected_trip_stop_times.csv"),DataFrame; types=Dict(:trip_id=>String))
stops.optimized_arrival_time=[hms(parse_hms(t)+60*shifts[string(j)]) for (j,t) in zip(stops.trip_id,stops.arrival_time)]
stops.optimized_departure_time=[hms(parse_hms(t)+60*shifts[string(j)]) for (j,t) in zip(stops.trip_id,stops.departure_time)]
CSV.write(joinpath(OUTPUTS,"jump_selected_trip_stop_times.csv"),stops)

println("Saved JuMP outputs. Compare against results/enumeration_results.json.")
