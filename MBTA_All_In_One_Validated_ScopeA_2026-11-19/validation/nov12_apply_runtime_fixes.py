#!/usr/bin/env python3
"""Apply targeted runtime-safety edits to the earlier Scope A Julia script.

These edits preserve the model, comments, and provenance. They were prepared
from the source listing in the conversation; the original project ZIP is not
available in this session. No Julia runtime or solver execution is claimed.
The input is left unchanged. A sibling *_reviewed.jl file is written by default.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from typing import Sequence

PATCHES: Sequence[tuple[str, str, str]] = (
    (
        "Preserve incoming clock fields as text",
        'incoming = CSV.read(joinpath(INPUTS, "incoming.csv"), DataFrame; types=Dict(:trip_id=>String, :route_id=>String))',
        'incoming = CSV.read(joinpath(INPUTS, "incoming.csv"), DataFrame;\n'
        '    types=Dict(:trip_id=>String, :route_id=>String,\n'
        '               :arrival_time=>String, :departure_time=>String))',
    ),
    (
        "Preserve outward service-day clock fields as text",
        'outgoing = CSV.read(joinpath(INPUTS, "outgoing.csv"), DataFrame; types=Dict(:trip_id=>String))',
        'outgoing = CSV.read(joinpath(INPUTS, "outgoing.csv"), DataFrame;\n'
        '    types=Dict(:trip_id=>String, :departure_time=>String))',
    ),
    (
        "Preserve shift-bound clock labels as text",
        'limits = CSV.read(joinpath(INPUTS, "shift_bounds_checked.csv"), DataFrame)',
        'limits = CSV.read(joinpath(INPUTS, "shift_bounds_checked.csv"), DataFrame;\n'
        '    types=Dict(:departure=>String))',
    ),
    (
        "Preserve complete-trip clock fields as text",
        'stops=CSV.read(joinpath(INPUTS,"selected_trip_stop_times.csv"),DataFrame; types=Dict(:trip_id=>String))',
        'stops=CSV.read(joinpath(INPUTS,"selected_trip_stop_times.csv"),DataFrame;\n'
        '    types=Dict(:trip_id=>String, :arrival_time=>String, :departure_time=>String))',
    ),
    (
        "Record solver outcome and require a feasible primal result",
        '''optimize!(model)
println("JuMP termination status: ",termination_status(model))
println("JuMP primal status: ",primal_status(model))
if !has_values(model)
    error("Solver returned no feasible timetable; inspect statuses and constraints")
end''',
        '''optimize!(model)
println("JuMP termination status: ",termination_status(model))
println("JuMP primal status: ",primal_status(model))
open(joinpath(OUTPUTS, "jump_solver_summary.txt"), "w") do io
    print(io, solution_summary(model))
end
if !has_values(model) || primal_status(model) != JuMP.MOI.FEASIBLE_POINT
    error("Solver returned no certified feasible primal result; inspect jump_solver_summary.txt")
end
optimality_proven = termination_status(model) == JuMP.MOI.OPTIMAL
if !optimality_proven
    @warn "A feasible incumbent is available, but global optimality was not established."
end''',
    ),
    (
        "Distinguish optimal assignment agreement from incumbent reevaluation",
        '@assert abs(mean_wait-objective_value(model))<1e-5',
        '''if optimality_proven
    @assert abs(mean_wait-objective_value(model)) < 1e-5
else
    # At a time limit, choosing the earliest feasible bus may improve the
    # incumbent's transfer assignment without changing its timetable.
    @assert mean_wait <= objective_value(model) + 1e-5
end''',
    ),
)

def apply_fixes(text: str) -> tuple[str, list[str]]:
    """Replace only recognized source blocks; reject mismatched versions."""
    changed: list[str] = []
    result = text
    for label, before, after in PATCHES:
        if after in result:
            continue
        count = result.count(before)
        if count != 1:
            raise ValueError(
                f"Cannot safely apply '{label}': expected one original block, found {count}. "
                "The script may differ from the reviewed source. No output was written."
            )
        result = result.replace(before, after, 1)
        changed.append(label)
    return result, changed

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Path to the existing src/run_scope_a.jl")
    parser.add_argument("--output", type=Path, help="Output file (must differ from input)")
    args = parser.parse_args()
    src = args.source.resolve()
    if not src.is_file() or src.suffix != ".jl":
        parser.error("source must be an existing Julia (.jl) file")
    dst = args.output.resolve() if args.output else src.with_name(src.stem + "_reviewed.jl")
    if dst == src:
        parser.error("output must differ from source; the original is preserved")
    if dst.exists():
        parser.error("output already exists; choose a new output path")
    revised, changes = apply_fixes(src.read_text(encoding="utf-8"))
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(revised, encoding="utf-8")
    print(f"Wrote {dst}; applied {len(changes)} targeted edits.")
    print("Julia execution and solver validation remain pending.")

if __name__ == "__main__":
    main()
