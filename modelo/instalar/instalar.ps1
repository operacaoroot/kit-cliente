# ============================================================================
#  instalar.ps1 - instalador do kit no Windows. ASCII puro de proposito:
#  o PowerShell 5.1 le .ps1 sem BOM como ANSI e acento quebra o script.
#
#  Jeito facil: clique duas vezes em instalar\instalar.cmd.
#  Na mao:      powershell -NoProfile -ExecutionPolicy Bypass -File instalar\instalar.ps1 [-Com vscode,docker]
#
#  O que faz (pode rodar quantas vezes quiser; o que ja existe e pulado):
#    1) Git (winget; o Windows pede permissao uma vez)
#    2) uv, que instala o Python sem senha de administrador
#    3) Python 3.12 e o Python do kit (.venv) com as bibliotecas
#    4) o resto do catalogo ambiente\apps.json pelo perfil do kit (o agente do kit, Obsidian...)
#       e o que o agente do kit pede (instalar\agente.ps1: Agente-Preparar)
#    5) liga o kit ao GitHub (conta da pessoa ou chave do kit), faz a ligacao do agente
#       (Agente-Ligar), cria o atalho (Agente-Atalho) e roda a conferencia
# ============================================================================
param([string]$Com = "")
$ErrorActionPreference = "Continue"
$Kit = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Kit
$Cliente = Get-Content (Join-Path $Kit ".root\cliente.json") -Raw -Encoding UTF8 | ConvertFrom-Json

function Passo($t) { Write-Host ""; Write-Host ("== " + $t) -ForegroundColor Cyan }
function Ok($t)    { Write-Host ("   ok  " + $t) -ForegroundColor Green }
function Aviso($t) { Write-Host ("   !!  " + $t) -ForegroundColor Yellow }
function Tem($c)   { $null -ne (Get-Command $c -ErrorAction SilentlyContinue) }
function Recarregar-Path {
  $partes = @(
    [Environment]::GetEnvironmentVariable("Path", "Machine"),
    [Environment]::GetEnvironmentVariable("Path", "User"),
    (Join-Path $env:USERPROFILE ".local\bin"),
    (Join-Path $env:ProgramFiles "Git\cmd")
  )
  $env:Path = ($partes | Where-Object { $_ }) -join ";"
}
function Fim($codigo) {
  Write-Host ""
  Read-Host "Tecle Enter para fechar esta janela" | Out-Null
  exit $codigo
}
# A parte que muda com o agente do kit mora em instalar\agente.ps1 (Agente-Preparar, Agente-Ligar,
# Agente-Atalho). O montador poe ali so a versao do agente deste kit.
. (Join-Path $PSScriptRoot "agente.ps1")

# acento vindo do Python nao pode derrubar o console (cp850)
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
Recarregar-Path

# ---------- 1) Git ----------
Passo "1/5 Git"
if (Tem git) { Ok "Git ja instalado" }
elseif (Tem winget) {
  Aviso "o Windows vai pedir permissao para instalar o Git: clique em Sim"
  winget install --id Git.Git -e --silent --accept-package-agreements --accept-source-agreements
  Recarregar-Path
  if (Tem git) { Ok "Git instalado" } else { Aviso "o Git nao ficou disponivel. Feche esta janela, abra de novo e rode outra vez."; Fim 1 }
}
else {
  Aviso "este Windows nao tem o winget. Instale o 'Instalador de Aplicativo' pela Microsoft Store e rode de novo."
  Start-Process "https://apps.microsoft.com/detail/9NBLGGH4NNS1"
  Fim 1
}

# ---------- 2) uv ----------
Passo "2/5 uv (instala o Python sem administrador)"
if (Tem uv) { Ok "uv ja instalado" }
else {
  Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
  Recarregar-Path
  if (Tem uv) { Ok "uv instalado" } else { Aviso "o uv nao ficou disponivel. Feche esta janela, abra de novo e rode outra vez."; Fim 1 }
}

# ---------- 3) Python do kit ----------
Passo "3/5 Python 3.12 e o Python do kit (.venv)"
uv python install 3.12
if ($LASTEXITCODE -ne 0) { Aviso "nao consegui preparar o Python 3.12."; Fim 1 }
$Py = Join-Path $Kit ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { uv venv --python 3.12 (Join-Path $Kit ".venv") }
if (Test-Path $Py) {
  uv pip install --quiet --python $Py -r (Join-Path $Kit "ambiente\requirements.txt")
  if ($LASTEXITCODE -ne 0) { Aviso "as bibliotecas do Python do kit nao ficaram prontas."; Fim 1 }
  Ok "Python do kit pronto"
} else { Aviso "nao consegui criar o Python do kit. Feche esta janela, abra de novo e rode outra vez."; Fim 1 }

# ---------- 4) o resto do catalogo ----------
Passo "4/5 Programas do kit (o agente, Obsidian e o que o seu perfil pede)"
$argsAmbiente = @("ferramentas\ambiente.py", "--instalar")
if ($Com) { $argsAmbiente += @("--com", $Com) }
& $Py @argsAmbiente
if ($LASTEXITCODE -ne 0) { Aviso "faltam programas obrigatorios; corrija o aviso acima e rode de novo."; Fim 1 }
Recarregar-Path

$global:LASTEXITCODE = 0
Agente-Preparar
if ($LASTEXITCODE -ne 0) { Aviso "a preparacao do agente nao terminou."; Fim 1 }

# ---------- 5) chave, atalho, conferencia ----------
Passo "5/5 GitHub, atalho e conferencia"
# Com usuario do GitHub no kit: entra com a conta da pessoa (colaborador).
# Sem conta, ou se o login nao terminar: liga pela chave do kit.
if ($Cliente.github) {
  & $Py ferramentas\conectar.py --conectar
  if ($LASTEXITCODE -ne 0) {
    Aviso "seguindo pela chave do kit; da para entrar no GitHub depois pelo agente do kit"
    & $Py ferramentas\conectar.py --usar-chave
    if ($LASTEXITCODE -ne 0) { Fim 1 }
  }
} else {
  & $Py ferramentas\conectar.py --usar-chave
  if ($LASTEXITCODE -ne 0) { Fim 1 }
}

Agente-Ligar
Agente-Atalho

& $Py ferramentas\ambiente.py --conferir
if ($LASTEXITCODE -ne 0) { Fim 1 }
& $Py ferramentas\verificar.py
if ($LASTEXITCODE -ne 0) { Fim 1 }
# Os demais passos do onboarding podem ficar pendentes; a instalacao precisa estar pronta.
try {
  $Progresso = Get-Content (Join-Path $Kit ".root\progresso.json") -Raw -Encoding UTF8 | ConvertFrom-Json
  $Instalacao = @($Progresso.passos | Where-Object { $_.id -eq "instalar" -and $_.feito -eq $true })
  if ($Instalacao.Count -eq 0) { Aviso "a instalacao ainda tem pendencias; corrija a conferencia e rode de novo."; Fim 1 }
} catch {
  Aviso "nao consegui conferir o resultado da instalacao."
  Fim 1
}
Fim 0
