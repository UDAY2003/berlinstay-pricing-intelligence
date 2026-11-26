# One command that proves the project is healthy (PowerShell):  .\scripts\check.ps1
# Uses the venv's Python directly, so the execution policy for Activate.ps1 does not matter.
$ErrorActionPreference = "Stop"
$py = ".\venv\Scripts\python.exe"
& $py -m src.run_v2;                 if ($LASTEXITCODE) { exit $LASTEXITCODE }
& $py -m src.build_app_data;         if ($LASTEXITCODE) { exit $LASTEXITCODE }
& $py -m src.powerbi_expected | Out-Null
& $py -m eval.run_eval --validate-gold; if ($LASTEXITCODE) { exit $LASTEXITCODE }
& $py -m pytest -q tests;            if ($LASTEXITCODE) { exit $LASTEXITCODE }
git status --short
"ALL CHECKS PASSED"
