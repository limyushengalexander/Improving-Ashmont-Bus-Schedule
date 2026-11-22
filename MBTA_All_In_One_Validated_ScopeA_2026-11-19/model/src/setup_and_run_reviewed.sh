#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v julia >/dev/null || { echo "Julia is not installed. Install Julia and rerun this script."; exit 127; }
mkdir -p results
julia --project=. -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()' 2>&1 | tee results/julia_setup.log
julia --project=. -e 'using Pkg, InteractiveUtils; versioninfo(); Pkg.status()' > results/julia_environment.txt 2>&1
julia --project=. src/run_scope_a_reviewed.jl 2>&1 | tee results/julia_run.log
echo "Julia run finished. Keep Manifest.toml, output CSVs and solver/environment logs."
