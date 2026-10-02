param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $Arguments
)

$ErrorActionPreference = 'Stop'
$runtimePath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $runtimePath)) {
    throw 'Create the environment first: py -3 -m venv .venv; .venv\Scripts\python.exe -m pip install -e ".[dev,bundle]" (Python 3.11+ required).'
}
& $runtimePath -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 2)'
if ($LASTEXITCODE -ne 0) {
    throw 'The .venv environment requires Python 3.11 or newer. Recreate it with a supported Python version.'
}
& $runtimePath -m portwatch @Arguments
exit $LASTEXITCODE
