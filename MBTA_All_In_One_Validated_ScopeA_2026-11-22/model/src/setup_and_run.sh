#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v julia >/dev/null || { echo "Julia is not installed. Install Julia 1.10+ and rerun."; exit 127; }
julia --project=. -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'
julia --project=. src/run_scope_a.jl
