# Nominal Scope A working model — November 22 working release

See the [release overview](../README_FIRST.md) and [November 22 current status](../docs/CURRENT_STATUS_2026-11-22.md). The model and computational results remain those verified on November 19; this revision updates the package and documentation. The original November 6 README is retained in `validation/README_original_Nov06.md` at the release root and the source ZIP.

- Inputs remain byte-identical to the archived, adopted nominal dataset.
- Original Python calculations have been rerun and reproduced.
- `src/run_scope_a.jl` is the original source.
- `src/run_scope_a_reviewed.jl` contains the applied source-safety revisions; it has NOT been run in Julia.
- Run `src/setup_and_run_reviewed.ps1` or `src/setup_and_run_reviewed.sh` with Julia installed.
- The latest heuristic and parameter experiments are in `../experiments/` and `../results/`, not in the earlier mathematical-formulation narrative.
- Initial November 6 report drafts are history; the current interim report is under `../latest_interim/`.
