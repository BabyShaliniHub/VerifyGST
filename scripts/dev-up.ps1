# Starts the local PostgreSQL and Neo4j containers and waits until both are healthy.
# Run with: powershell -NoProfile -ExecutionPolicy Bypass -File C:\VerifiGST\scripts\dev-up.ps1
$compose = Join-Path $PSScriptRoot '..\docker-compose.yml'
docker compose -f $compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Docker is not running or the start failed. Open Docker Desktop, wait until it is running, then run this again.'
    exit 1
}
$names = 'verifigst-postgres', 'verifigst-neo4j'
for ($i = 0; $i -lt 40; $i++) {
    $states = $names | ForEach-Object { docker inspect --format '{{.State.Health.Status}}' $_ 2>$null }
    if ((@($states).Count -eq 2) -and (@($states | Where-Object { $_ -ne 'healthy' }).Count -eq 0)) {
        Write-Host 'Both databases are healthy.'
        exit 0
    }
    Start-Sleep -Seconds 3
}
Write-Host 'The databases were not healthy after two minutes. Current state:'
docker compose -f $compose ps
exit 1
