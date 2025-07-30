<#
.SYNOPSIS
  Setup do ambiente para o Book Scanner no Windows.
#>
If (-Not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
  Write-Error "Execute este script como Administrador."
  Exit 1
}

# Instalar Chocolatey (se não existir)
If (-Not (Get-Command choco -ErrorAction SilentlyContinue)) {
  Write-Output "Instalando Chocolatey..."
  Set-ExecutionPolicy Bypass -Scope Process -Force
  [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
  Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
}

choco feature enable -n allowGlobalConfirmation
choco install python --version=3.11.5 ffmpeg tesseract -y

# Atualiza PATH para sessão atual
$env:Path = "$env:ProgramFiles\Python311\;$env:Path"

# Projeto
$proj = "C:\book-scanner"
If (-Not (Test-Path $proj)) { New-Item -Path $proj -ItemType Directory | Out-Null }
Write-Output "Projeto em $proj"

# Virtualenv e deps
Write-Output "Criando virtualenv e instalando dependências..."
Push-Location $proj
python -m venv venv
& "$proj\venv\Scripts\Activate.ps1"
pip install --upgrade pip
pip install opencv-python watchdog img2pdf flask pillow pytesseract
Pop-Location

# Pastas
Write-Output "Criando pastas..."
New-Item -ItemType Directory -Force -Path `
  "$proj\processors", `
  "$proj\templates", `
  "$proj\static\css", `
  "$proj\static\js", `
  "$proj\data\sessions" | Out-Null

Write-Output "✅ Setup concluído! Execute:`n  cd $proj`n  .\\venv\\Scripts\\Activate.ps1`n  flask run --host=0.0.0.0"
