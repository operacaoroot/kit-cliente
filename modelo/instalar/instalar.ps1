# Instalador do kit (Windows). Clique com o botão direito e escolha "Executar com o PowerShell".
# Instala o que faltar, liga a chave do kit ao git e roda a conferência.
# Pode rodar quantas vezes quiser: o que já está instalado é pulado.
$ErrorActionPreference = "Continue"
$Kit = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Kit

function Passo($t) { Write-Host "`n== $t" -ForegroundColor Cyan }
function Falha($t) { Write-Host "`n[atenção] $t" -ForegroundColor Yellow }
function Tem($c) { $null -ne (Get-Command $c -ErrorAction SilentlyContinue) }
function Recarregar-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User") + ";$env:USERPROFILE\.local\bin"
}

Passo "Conferindo o git, o Python e o Obsidian"
if (-not (Tem winget)) {
  Falha "O Windows não tem o winget. Instale o 'Instalador de Aplicativo' pela Microsoft Store e rode de novo."
} else {
  if (-not (Tem git)) { winget install --id Git.Git -e --silent --accept-package-agreements --accept-source-agreements }
  if (-not (Tem py)) { winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements }
  $obs = @("$env:LOCALAPPDATA\Obsidian\Obsidian.exe", "$env:LOCALAPPDATA\Programs\Obsidian\Obsidian.exe") | Where-Object { Test-Path $_ }
  if (-not $obs) { winget install --id Obsidian.Obsidian -e --silent --accept-package-agreements --accept-source-agreements }
  Recarregar-Path
}
if (Tem git) { Write-Host "git ok" } else { Falha "git não ficou disponível. Feche esta janela, abra de novo e rode outra vez." }
if (Tem py) { Write-Host "Python ok" } else { Falha "Python não ficou disponível. Feche esta janela, abra de novo e rode outra vez." }

Passo "Conferindo o Claude Code"
if (-not (Tem claude)) {
  Write-Host "Instalando o Claude Code pelo instalador oficial..."
  Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression
  Recarregar-Path
}
if (Tem claude) { Write-Host "Claude Code ok" } else { Falha "O Claude Code não ficou disponível. Feche esta janela, abra de novo e rode outra vez." }

Passo "Ligando a chave do kit"
$Chave = Join-Path $Kit ".root\chave"
if (Test-Path $Chave) {
  icacls $Chave /inheritance:r /grant:r "$($env:USERNAME):(R)" | Out-Null
  $ChaveGit = $Chave -replace '\\', '/'
  git config core.sshCommand "ssh -i `"$ChaveGit`" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
  $Cliente = Get-Content (Join-Path $Kit ".root\cliente.json") -Raw | ConvertFrom-Json
  git config user.name $Cliente.nome
  git config user.email "kit-$($Cliente.slug)@kit.operacaoroot.com"
  Write-Host "chave ligada"
} else {
  Falha "A chave do kit (.root\chave) não veio junto. Fale com a Root."
}

Passo "Criando o atalho do Claude do kit"
$Atalho = Join-Path ([Environment]::GetFolderPath("Desktop")) "Claude do kit.cmd"
"@echo off`r`ncd /d `"$Kit`"`r`nclaude`r`n" | Set-Content -Path $Atalho -Encoding ASCII
Write-Host "atalho criado na Área de Trabalho: Claude do kit"

Passo "Conferência"
py ferramentas\verificar.py
Read-Host "`nPronto. Tecle Enter para fechar esta janela"
