$ErrorActionPreference = "Stop"

$project = "automate-511215"
$region = "asia-south1"

foreach ($tool in @("gcloud", "firebase")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "Required command '$tool' was not found. Install it and authenticate before rerunning."
    }
}

$billingJson = & gcloud billing projects describe $project --format=json
if ($LASTEXITCODE -ne 0) {
    throw "Could not read billing status for project '$project'. No shutdown actions were run."
}

$billing = $billingJson | ConvertFrom-Json
if ($billing.projectId -ne $project) {
    throw "Billing status returned unexpected project '$($billing.projectId)'. No shutdown actions were run."
}
if (-not $billing.billingEnabled) {
    Write-Output "Billing is already disabled for '$project'; no actions were run."
    exit 0
}

Write-Output "This will delete the app's Cloud Run services, quota guard, Scheduler job, and Gemini secret; publish a blank Hosting page; and unlink project billing."
Write-Output "Firestore data, the Firebase project, and other retained resources will not be deleted."
$confirmation = Read-Host "Type SHUTDOWN to continue"
if ($confirmation -cne "SHUTDOWN") {
    Write-Output "Cancelled; no shutdown actions were run."
    exit 0
}

$failures = New-Object 'System.Collections.Generic.List[string]'
function Invoke-ShutdownStep {
    param(
        [string]$Label,
        [scriptblock]$Action
    )

    Write-Output "`n--- $Label ---"
    try {
        & $Action
        if ($LASTEXITCODE -ne 0) {
            throw "Command exited with code $LASTEXITCODE."
        }
    } catch {
        $script:failures.Add("$Label`: $($_.Exception.Message)")
        Write-Warning "$Label failed: $($_.Exception.Message)"
    }
}

Invoke-ShutdownStep "Pause quota guard schedule" {
    & gcloud scheduler jobs pause quota-guard-every-five-minutes `
        --location=$region --project=$project --quiet
}

Invoke-ShutdownStep "Delete quota guard schedule" {
    & gcloud scheduler jobs delete quota-guard-every-five-minutes `
        --location=$region --project=$project --quiet
}

Invoke-ShutdownStep "Delete quota guard function" {
    & gcloud functions delete quota-guard --gen2 `
        --region=$region --project=$project --quiet
}

Invoke-ShutdownStep "Delete application API service" {
    & gcloud run services delete sustainbite-api `
        --region=$region --project=$project --quiet
}

Invoke-ShutdownStep "Delete Gemini API secret" {
    & gcloud secrets delete GEMINI_API_KEY --project=$project --quiet
}

$tempRoot = Join-Path $env:TEMP ("sustainbite-shutdown-" + [guid]::NewGuid().ToString("N"))
$publicDir = Join-Path $tempRoot "public"
try {
    New-Item -ItemType Directory -Path $publicDir -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $tempRoot "firebase.json") `
        -Value '{"hosting":{"public":"public","ignore":["firebase.json","**/.*","**/node_modules/**"]}}' `
        -Encoding Ascii
    Set-Content -LiteralPath (Join-Path $publicDir "index.html") `
        -Value '<!doctype html><html><head><meta charset="utf-8"><title></title></head><body></body></html>' `
        -Encoding Ascii

    Invoke-ShutdownStep "Replace Firebase Hosting app with a blank page" {
        & firebase deploy --config (Join-Path $tempRoot "firebase.json") `
            --only hosting --project $project
    }
} catch {
    $failures.Add("Prepare blank Hosting page: $($_.Exception.Message)")
    Write-Warning "Prepare blank Hosting page failed: $($_.Exception.Message)"
} finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}

Invoke-ShutdownStep "Unlink project billing" {
    & gcloud billing projects unlink $project --quiet
}

if ($failures.Count -gt 0) {
    Write-Error ("Shutdown finished with errors:`n - " + ($failures -join "`n - "))
    exit 1
}

Write-Output "`nShutdown commands completed. Verify billing with:"
Write-Output "gcloud billing projects describe $project --format='yaml(projectId,billingAccountName,billingEnabled)'"
