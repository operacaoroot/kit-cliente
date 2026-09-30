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
#    4) o resto do catalogo ambiente\apps.json pelo perfil do kit (Claude Code, Obsidian...)
#    5) liga o kit ao GitHub (conta da pessoa ou chave do kit), cria o atalho e roda a conferencia
# ============================================================================
param([string]$Com = "")
$ErrorActionPreference = "Continue"
$Kit = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Kit

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
  if (Tem git) { Ok "Git instalado" } else { Aviso "o Git nao ficou disponivel. Feche esta janela, abra de novo e rode outra vez." }
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
$Py = Join-Path $Kit ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { uv venv --python 3.12 (Join-Path $Kit ".venv") }
if (Test-Path $Py) {
  uv pip install --quiet --python $Py -r (Join-Path $Kit "ambiente\requirements.txt")
  Ok "Python do kit pronto"
} else { Aviso "nao consegui criar o Python do kit. Feche esta janela, abra de novo e rode outra vez."; Fim 1 }

# ---------- 4) o resto do catalogo ----------
Passo "4/5 Claude Code, Obsidian e o que o seu perfil pede"
$argsAmbiente = @("ferramentas\ambiente.py", "--instalar")
if ($Com) { $argsAmbiente += @("--com", $Com) }
& $Py @argsAmbiente
Recarregar-Path

# ---------- 5) chave, atalho, conferencia ----------
Passo "5/5 GitHub, atalho e conferencia"
# Com usuario do GitHub no kit: entra com a conta da pessoa (colaborador).
# Sem conta, ou se o login nao terminar: liga pela chave do kit.
$Cliente = Get-Content (Join-Path $Kit ".root\cliente.json") -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Cliente.github) {
  & $Py ferramentas\conectar.py --conectar
  if ($LASTEXITCODE -ne 0) {
    Aviso "seguindo pela chave do kit; da para entrar no GitHub depois pelo Claude do kit"
    & $Py ferramentas\conectar.py --usar-chave
  }
} else {
  & $Py ferramentas\conectar.py --usar-chave
}

$Atalho = Join-Path ([Environment]::GetFolderPath("Desktop")) "Claude do kit.cmd"
$linhas = @("@echo off", ("cd /d """ + $Kit + """"), "set PATH=%USERPROFILE%\.local\bin;%PATH%", "claude")
[System.IO.File]::WriteAllText($Atalho, (($linhas -join "`r`n") + "`r`n"), (New-Object System.Text.ASCIIEncoding))
if (Test-Path $Atalho) { Ok "atalho criado na Area de Trabalho: Claude do kit" } else { Aviso "nao consegui criar o atalho; abra a pasta do kit e rode claude" }

# rotina que alimenta o vault: so se foi combinada no kickoff (cliente.json, rotina_do_vault.ligar)
$Rotina = $Cliente.rotina_do_vault
if ($Rotina -and $Rotina.ligar) {
  $argsRotina = @("ferramentas\rotina.py", "--ligar", "--horas", (($Rotina.horas) -join ","))
  if ($Rotina.enviar -eq $false) { $argsRotina += "--sem-envio" }
  & $Py @argsRotina
} else {
  Ok "rotina do vault nao combinada; para ligar depois, peca ao Claude do kit: liga a rotina do vault"
}

& $Py ferramentas\ambiente.py --conferir
& $Py ferramentas\verificar.py
Fim 0
