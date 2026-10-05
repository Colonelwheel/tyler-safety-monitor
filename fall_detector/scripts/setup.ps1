# Create a new isolated environment only; never modify global Python packages.
$ErrorActionPreference = 'Stop'
$taskDetectorRoot = Split-Path -Parent $PSScriptRoot
$taskEnvironment = Join-Path $taskDetectorRoot '.venv'
if (Test-Path -LiteralPath $taskEnvironment) {
    throw 'An environment already exists. It was preserved; use its python or review a new environment path.'
}
& py -3.12 -m venv $taskEnvironment
if ($LASTEXITCODE -ne 0) { throw 'Environment creation failed; global Python was not modified.' }
$taskPython = Join-Path $taskEnvironment 'Scripts\python.exe'
& $taskPython -m pip --isolated --disable-pip-version-check install --no-cache-dir -r (Join-Path $taskDetectorRoot 'requirements.lock')
if ($LASTEXITCODE -ne 0) { throw 'Isolated dependency installation failed.' }
& $taskPython -m pip --isolated --disable-pip-version-check install --no-deps --no-build-isolation -e $taskDetectorRoot
if ($LASTEXITCODE -ne 0) { throw 'Isolated application installation failed.' }
& $taskPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency verification failed.' }
Write-Output 'Ready. Start with fall_detector\Start Monitor.cmd. Models are downloaded explicitly.'
