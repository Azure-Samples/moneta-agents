$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
  # fallback to python3 if python not found
  $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}

Write-Host 'Uploading initial data to AI Search and Cosmos DB...'
Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/data_load/setup_aisearch.py" -Wait -NoNewWindow
Start-Process -FilePath $venvPythonPath -ArgumentList "./scripts/data_load/setup_cosmosdb.py" -Wait -NoNewWindow