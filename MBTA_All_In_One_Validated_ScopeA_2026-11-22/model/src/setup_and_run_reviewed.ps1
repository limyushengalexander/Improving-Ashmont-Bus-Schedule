$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Get-Command julia -ErrorAction SilentlyContinue)) { throw "Julia is not installed or is not on PATH." }
New-Item -ItemType Directory -Force -Path results | Out-Null
& julia --project=. -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()' *> results/julia_setup.log
if ($LASTEXITCODE -ne 0) { throw "Julia setup failed. See results/julia_setup.log." }
& julia --project=. -e 'using Pkg, InteractiveUtils; versioninfo(); Pkg.status()' *> results/julia_environment.txt
if ($LASTEXITCODE -ne 0) { throw "Environment logging failed. See results/julia_environment.txt." }
& julia --project=. src/run_scope_a_reviewed.jl *> results/julia_run.log
if ($LASTEXITCODE -ne 0) { throw "Julia run failed. See results/julia_run.log." }
Get-Content results/julia_run.log
Write-Output "Keep Manifest.toml, output CSVs and solver/environment logs."
