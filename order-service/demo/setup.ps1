$ErrorActionPreference = 'Stop'
$demoEnvPath = Join-Path $PSScriptRoot '.env'
if (Test-Path -LiteralPath $demoEnvPath) {
    Write-Host 'Demo .env already exists; leaving it unchanged.'
    exit 0
}
function New-DemoSecret {
    $demoBytes = New-Object byte[] 32
    $demoRng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $demoRng.GetBytes($demoBytes) } finally { $demoRng.Dispose() }
    return ([BitConverter]::ToString($demoBytes)).Replace('-', '').ToLowerInvariant()
}
$demoContents = @(
    "DEMO_DB_PASSWORD=$(New-DemoSecret)"
    "DEMO_APP_PASSWORD=$(New-DemoSecret)"
    "DEMO_BROKER_PASSWORD=$(New-DemoSecret)"
    "DEMO_CREDIT_SECRET=$(New-DemoSecret)"
    'SIMULATOR_MODE=success'
)
# CreateNew refuses to overwrite even if another setup starts concurrently.
$demoStream = [System.IO.File]::Open($demoEnvPath, 'CreateNew', 'Write')
$demoWriter = [System.IO.StreamWriter]::new($demoStream)
try { $demoWriter.WriteLine($demoContents -join "`n") } finally { $demoWriter.Dispose() }
Write-Host 'Created ignored demo-only configuration. No existing service settings were changed.'
