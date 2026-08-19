# Start backend if not running, then run tests
$ErrorActionPreference = "Continue"

# Check if backend is running on port 8000
$backendRunning = $false
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -Method Get -TimeoutSec 5
    $backendRunning = $true
    Write-Host "Backend already running: $($response.status)"
} catch {
    Write-Host "Backend not running, starting..."
}

if (-not $backendRunning) {
    # Start backend in background
    Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "tros.api.app:app", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory "c:\Users\HP\Documents\hackathon Atlas" -WindowStyle Hidden
    Write-Host "Waiting for backend to start..."
    Start-Sleep -Seconds 8

    # Verify backend is now running
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -Method Get -TimeoutSec 5
        Write-Host "Backend started: $($response.status)"
    } catch {
        Write-Host "Backend failed to start: $_"
    }
}

# Run the test script
Write-Host "Running live scenario tests..."
python "c:\Users\HP\Documents\hackathon Atlas\live_test.py"

# Read and display results
Write-Host "`n--- RESULTS FILE ---"
if (Test-Path "c:\Users\HP\Documents\hackathon Atlas\live_test_results.txt") {
    Get-Content "c:\Users\HP\Documents\hackathon Atlas\live_test_results.txt" -Raw
} else {
    Write-Host "Results file not found"
}
