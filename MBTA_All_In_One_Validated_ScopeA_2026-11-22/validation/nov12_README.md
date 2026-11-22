# Latest code update — not the complete model

The two files here are byte-identical copies of the November 12 report revision package. The patcher needs the real November 6 `src/run_scope_a.jl`; that source and its input CSV files are not in this partial consolidation.

After restoring and extracting the original model ZIP, run:

```bash
python 02_code_updates/apply_runtime_fixes.py /path/to/MBTA_ScopeA_Nov06_Model/src/run_scope_a.jl
```

This writes a separate reviewed Julia file beside the original so the original model's relative paths remain valid. It preserves the original source. The patch is not applied automatically by the packaging tool. Julia execution and solver validation remain pending.

The supplied `Code_Review.md` retains its original relative-path instructions and historical context. The invocation above reflects this consolidation's folder names.
