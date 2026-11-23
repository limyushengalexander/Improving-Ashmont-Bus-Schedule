# MBTA Ashmont — validated Scope A experiments and complete source collection
**Latest working release: November 22, 2026**

**Computational evidence: November 19, 2026**

**Team:** Alex Lim, Yun Ji Seo, Luran Wang

## Read first

Open [the review memo](docs/Scope_A_Validation_Experiments_2026-11-22.pdf) for the six-page review, or [the experiment findings](docs/VALIDATION_AND_EXPERIMENT_FINDINGS.md) for the detailed text. The memo is working evidence, not the final course report. [Current status](docs/CURRENT_STATUS_2026-11-22.md) distinguishes completed work from remaining tasks. The [explained project guide](docs/MBTA_Ashmont_Project_Explained_Up_to_Interim_Report_2026-11-22.md) covers the model, worked examples, interim report, and later experiment findings.

The November 22 revision updates package names, documentation, references, and integrity metadata. The memo's PDF/DOCX filenames now use November 22 to match the working release; their contents still record the November 19 analysis. No optimization, experiment, or Julia run was newly performed for this revision. The original `MBTA_All_In_One_Validated_ScopeA_2026-11-19.zip` remains the unchanged reference snapshot; this working folder supersedes its navigation and documentation, while preserving the computational evidence.

**New result:** the original 13.5122-to-12.4634-minute scheduled improvement reproduces. The simple chronological heuristic obtains the **same** result. The unchanged nominal-optimal timetable is sensitive to the assumed passenger transfer allowance; under five minutes it is worse than the original timetable, although reoptimization can improve performance. Do not describe the current timetable as robust to delays or transfer-time uncertainty.

**Julia execution remains pending.** The recorded November 19 authoring environment had no Julia executable, and official runtime retrieval failed. No later Julia execution evidence has been added. The reviewed Julia source, application environment and Windows/macOS/Linux run instructions are included; none is presented as an executed Julia result. The Python MILP and enumeration calculations actually ran.

## Is this package complete?

All **eight uploaded ZIP archives** are included unchanged under `source_archives/`, along with the unpacked current working code, nominal input data, new experiment results and current interim report. The previously uploaded file whose name ends in `_PARTIAL` remains preserved as a historical source; its old missing-file inventory is superseded by this release.

Complete source collection does **not** mean the entire term project is finished. Julia execution, Scope B, and final technical report/slides/video are not completed here. The one-page November 12 interim report is included unchanged; do not silently substitute this newer experiment memo for a previously submitted report.

## Where to find everything

| Path | Contents/status |
|---|---|
| `model/inputs/` | Frozen nominal October 15 model tables and adopted assumptions |
| `model/src/run_scope_a.jl` | Original Julia source, retained unchanged |
| `model/src/run_scope_a_reviewed.jl` | Runtime-safety revisions applied to the actual source; Julia execution pending |
| `model/Project.toml` | Application dependency environment; Manifest generated only on actual installation |
| `model/src/reference_enumeration.py` | Original independent enumeration, rerun successfully |
| `model/src/check_milp_with_scipy.py` | Original SciPy MILP check, rerun successfully |
| `model/results/` | Reproduced nominal results; actual Julia outputs will appear here only after a Julia run |
| `experiments/experiment_plan.json` | Frozen benchmark and 38-case definitions |
| `experiments/scope_a_experiments.py` | Parameterized model, primary/supplementary heuristics, enumeration and all case execution |
| `results/experiment_summary.csv` | One row per case: feasibility, solver, original/heuristic/reoptimized/frozen performance |
| `results/cases/` | Case parameters, regenerated domains, solver certificates, enumeration records, per-opportunity results and constraints |
| `results/nominal_method_comparison.csv` | Existing versus simple heuristic versus optimized comparison |
| `results/transfer_allowance_stress_test.csv` | Distinguishes reoptimization from evaluating the same nominal timetable |
| `results/individual_transfer_changes.csv` | All 41 individual effects |
| `results/optimized_complete_trip_stop_times.csv` | All 300 selected-trip stop rows shifted consistently |
| `figures/` | Four separate PNG figures and their reproducible code in `experiments/make_figures.py` |
| `validation/` | Baseline lock, source hashes, actual run logs, tests, independent checks and Julia-status records |
| `latest_interim/` | Latest November 12 v2 DOCX/PDF/Markdown, unchanged |
| [TA discussion deck](presentations/MBTA_Ashmont_TA_Review_2026-11-22.pptx) | Five slides with speaker notes, explaining work through the November 12 interim report and questions for TA guidance |
| `docs/` | New validation memo, methods, findings, current status and source register |
| `course_requirements/` | Original term-project description recovered from the consolidation |
| `source_archives/` | All eight original archives, unmodified |

Files inside `source_archives` describe their historical status; use the November 22 current-status document and root release metadata for the current state, and the November 19 memo for the recorded computational findings. The initial mathematical formulation remains under `model/docs/`; the new experiment definitions do not overwrite that source record.

## What was executed on November 19?

- Fresh raw-GTFS extraction with eight matching input outputs.
- Original Python enumeration and SciPy/HiGHS MILP, recovering 71,673 feasible nominal timetables and the same unique optimum.
- Primary single chronological pass and supplementary repeated-pass heuristic.
- **38 cases:** 27 crossed parameter cases, eight additional sensitivity/boundary/grid cases and three constraint removals. **32 optimal feasible cases**, six analytically infeasible cases; 31 optima independently enumerated.
- **12 original plus 34 new tests**; 5,740 independent earliest-departure row checks; 300 shifted stop-time rows and 33 block-neighbor pairs audited.

Not executed: Julia/JuMP, Scope B, new raw-data collection, final-report or presentation production. An infeasible case is explicitly retained, not assigned a manufactured improvement or silently removed.

## Reproduce Python work

Use Python 3.13 with versions in `requirements-python.txt` for the recorded environment. From this folder:

```bash
python -m pip install -r requirements-python.txt
python model/src/reference_enumeration.py
python model/src/check_milp_with_scipy.py
python -m unittest discover -s model/tests -v
python experiments/scope_a_experiments.py
python experiments/summarize_and_audit.py
python -m unittest discover -s tests -v
python experiments/make_figures.py
```

The code reads frozen files locally; it does not query a rolling live MBTA feed. Rerunning overwrites working result files and changes timing logs, so keep the downloaded ZIP unchanged as the release snapshot. The original archive records remain separate.

Raw-to-CSV reconstruction, with a new empty output directory:

```bash
python validation/prepare_scope_a_original.py --input source_archives/20261014.zip --config model/inputs/adopted_scope_a_config.json --out validation/rebuilt_local
```

`PROVISIONAL_REQUIRES_REVIEW` in that original script is deliberate: real operational assumptions are not certified and the script does not query the historical archive index itself. Do not change this flag simply to make a run look successful.

## Finish Julia verification

With Julia installed, run the appropriate script:

```bash
# macOS/Linux, from this release folder:
bash model/src/setup_and_run_reviewed.sh

# Windows PowerShell, from this release folder:
# .\model\src\setup_and_run_reviewed.ps1
```

Then run:

```bash
python validation/verify_julia_outputs.py
```

The verifier requires actual `jump_*` files, a solver status/feasibility certificate, all 41 baseline/optimized waits, and the six shifts. Do not manufacture those files from Python outputs. Save the generated `Manifest.toml`, Julia environment details and solver log alongside the model. Expected nominal mean is 12.46341463414634 minutes; shifts in chronological departure order are `[-2,0,-2,-1,+2,0]` minutes. These are regression targets, not fixed optimization choices.

## Packaging and integrity

`FILE_INVENTORY.txt` lists the current working-release files. The root `manifest_sha256.json` records their sizes and SHA-256 hashes, excluding the manifest itself. Run `python validation/verify_release_manifest.py` before modifying or rerunning the package. The manifests under `model/` and `validation/original_model_manifest_sha256.json` retain earlier model provenance; the root manifest describes this November 22 working release. No new November 22 outer ZIP or companion ZIP checksum is included in this revision. Logs and flags are not substitutes for actual model execution.

## Project interpretation

We model equally weighted incoming-trip opportunities, not measured transfer passengers. Operating turnaround, berth movement, transfer readiness and headway rules are declared assumptions. Small scheduled changes are candidates for operational review, not an MBTA-approved timetable. The heuristic tie and transfer-time fragility must be retained in the final interpretation. Scope B's historical date matching, timestamp conventions and delayed Quincy vehicle availability remain open.

This release includes AI-assisted review, code changes, experiment execution and documentation. Provenance and original artifacts are preserved; the team should review the analysis and follow course authorship/disclosure requirements.
