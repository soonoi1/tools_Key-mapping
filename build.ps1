$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
  python -m venv .venv
}

.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements.txt

.\.venv\Scripts\python -m unittest discover -s tests
.\.venv\Scripts\python -m key_mapper_sdk --check
.\.venv\Scripts\pyinstaller --clean --name KeyMapperSDK --onefile key_mapper_sdk_launcher.py
.\.venv\Scripts\pyinstaller --clean --name KeyFlowMapper --onefile --windowed keyflow_mapper_app.py

Get-Process KeyMapperSDK, KeyFlowMapper -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

if (Test-Path release) {
  Remove-Item release -Recurse -Force
}
New-Item -ItemType Directory -Force -Path release | Out-Null
Copy-Item dist\KeyMapperSDK.exe release\KeyMapperSDK.exe -Force
Copy-Item dist\KeyFlowMapper.exe release\KeyFlowMapper.exe -Force
New-Item -ItemType Directory -Force -Path release\config | Out-Null
Copy-Item config\mappings.json release\config\mappings.json -Force
Copy-Item README.md release\README.md -Force

Start-Sleep -Seconds 2
Compress-Archive -Path release\* -DestinationPath release\KeyMapperSDK.zip -Force
Write-Host "Built release\KeyFlowMapper.exe, release\KeyMapperSDK.exe, and release\KeyMapperSDK.zip"
