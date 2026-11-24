# ============================================================================
#  instalar.ps1 - instalador do kit no Windows. ASCII puro de proposito:
#  o PowerShell 5.1 le .ps1 sem BOM como ANSI e acento quebra o script.
#
#  Jeito facil: clique duas vezes em instalar\instalar.cmd.
#  Na mao:      powershell -NoProfile -ExecutionPolicy Bypass -File instalar\instalar.ps1 [-Com vscode,docker]
#
#  O que faz (pode rodar quantas vezes quiser; o que ja existe e pulado):
#    1) uv, que instala o Python sem senha de administrador
#    2) Python 3.12 e o Python do kit (.venv) com as bibliotecas
#       -> a partir daqui o Painel do kit abre no navegador e mostra tudo o que acontece
#    3) Git (winget; o Windows pede permissao uma vez)
#    4) o resto do catalogo ambiente\apps.json pelo perfil do kit (o agente do kit, Obsidian...)
#       e o que o agente do kit pede (instalar\agente.ps1: Agente-Preparar)
#    5) liga o kit a Root pela chave que veio no kit (sem conta nem codigo do GitHub)
#    6) faz a ligacao do agente (Agente-Ligar), cria os atalhos (Agente-Atalho e Painel do kit)
#       e roda a conferencia; o painel mostra o que falta e os proximos passos
# ============================================================================
param([string]$Com = "")
$ErrorActionPreference = "Continue"
$Kit = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Kit
$Cliente = Get-Content (Join-Path $Kit ".root\cliente.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$Py = Join-Path $Kit ".venv\Scripts\python.exe"

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
# O painel e so vitrine: se falhar, a instalacao segue.
function Painel {
  if (Test-Path $Py) { & $Py ferramentas\painel.py @args *> $null }
}
function Fim($codigo) {
  Write-Host ""
  Read-Host "Tecle Enter para fechar esta janela" | Out-Null
  exit $codigo
}
# Depois que o painel abriu: fecha a conferencia nele antes de sair, para a pagina nao ficar parada.
function Parar($codigo) {
  Painel concluir --interrompido
  Fim $codigo
}
# A parte que muda com o agente do kit mora em instalar\agente.ps1 (Agente-Preparar, Agente-Ligar,
# Agente-Atalho). O montador poe ali so a versao do agente deste kit.
. (Join-Path $PSScriptRoot "agente.ps1")

# acento vindo do Python nao pode derrubar o console (cp850)
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
Recarregar-Path

# ---------- 1) uv ----------
Passo "1/6 uv (instala o Python sem administrador)"
if (Tem uv) { Ok "uv ja instalado" }
else {
  Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
  Recarregar-Path
  if (Tem uv) { Ok "uv instalado" } else { Aviso "o uv nao ficou disponivel. Feche esta janela, abra de novo e rode outra vez."; Fim 1 }
}

# ---------- 2) Python do kit ----------
Passo "2/6 Python 3.12 e o Python do kit (.venv)"
uv python install 3.12
if ($LASTEXITCODE -ne 0) { Aviso "nao consegui preparar o Python 3.12."; Fim 1 }
if (-not (Test-Path $Py)) { uv venv --python 3.12 (Join-Path $Kit ".venv") }
if (Test-Path $Py) {
  uv pip install --quiet --python $Py -r (Join-Path $Kit "ambiente\requirements.txt")
  if ($LASTEXITCODE -ne 0) { Aviso "as bibliotecas do Python do kit nao ficaram prontas."; Fim 1 }
  Ok "Python do kit pronto"
} else { Aviso "nao consegui criar o Python do kit. Feche esta janela, abra de novo e rode outra vez."; Fim 1 }

Painel iniciar "--abrir"
Painel etapa python ok "Python do kit pronto"
Write-Host "   ..  o Painel do kit abriu no navegador: ele mostra o que esta acontecendo e o que falta"

# ---------- 3) Git ----------
Passo "3/6 Git"
Painel etapa basico andamento "conferindo o Git"
if (Tem git) { Ok "Git ja instalado"; Painel etapa basico ok "Git, uv e Python prontos" }
elseif (Tem winget) {
  Aviso "o Windows vai pedir permissao para instalar o Git: clique em Sim"
  Painel evento "O Windows vai pedir permissao para instalar o Git: clique em Sim." "--tipo" aviso
  winget install --id Git.Git -e --silent --accept-package-agreements --accept-source-agreements
  Recarregar-Path
  if (Tem git) { Ok "Git instalado"; Painel etapa basico ok "Git, uv e Python prontos" }
  else {
    Aviso "o Git nao ficou disponivel. Feche esta janela, abra de novo e rode outra vez."
    Painel etapa basico falhou "o Git nao ficou disponivel; rode o instalador de novo"
    Parar 1
  }
}
else {
  Aviso "este Windows nao tem o winget. Instale o 'Instalador de Aplicativo' pela Microsoft Store e rode de novo."
  Painel etapa basico falhou "falta o Instalador de Aplicativo (winget) da Microsoft Store"
  Start-Process "https://apps.microsoft.com/detail/9NBLGGH4NNS1"
  Parar 1
}

# ---------- 4) o resto do catalogo ----------
Passo "4/6 Programas do kit (o agente, Obsidian e o que o seu perfil pede)"
Painel etapa programas andamento "instalando o que falta; o Windows pode pedir permissao, clique em Sim"
$argsAmbiente = @("ferramentas\ambiente.py", "--instalar")
if ($Com) { $argsAmbiente += @("--com", $Com) }
& $Py @argsAmbiente
if ($LASTEXITCODE -ne 0) {
  Aviso "faltam programas obrigatorios; corrija o aviso acima e rode de novo."
  Painel etapa programas falhou "faltam programas obrigatorios; veja a lista do que falta"
  Parar 1
}
Painel etapa programas ok "programas do kit instalados"
Recarregar-Path

Painel etapa autonomia andamento
$global:LASTEXITCODE = 0
Agente-Preparar
if ($LASTEXITCODE -ne 0) {
  Aviso "a preparacao do agente nao terminou."
  Painel etapa autonomia falhou "a preparacao do agente nao terminou"
  Parar 1
}
Painel etapa autonomia ok "o agente do kit esta pronto para trabalhar"

# ---------- 5) chave do kit ----------
Passo "5/6 Ligando o kit a Root"
# Sempre pela chave que veio no kit: sem conta, sem login e sem codigo do GitHub.
Painel etapa chave andamento "pela chave que veio no kit"
& $Py ferramentas\conectar.py --usar-chave
if ($LASTEXITCODE -ne 0) {
  Painel etapa chave falhou "a chave do kit nao veio no ZIP; extraia o ZIP inteiro de novo"
  Parar 1
}
Painel etapa chave ok "kit ligado pela chave; sem conta nem codigo do GitHub"

# ---------- 6) agente, atalhos e conferencia ----------
Passo "6/6 Atalhos e conferencia"
Agente-Ligar
Painel etapa atalho andamento
Agente-Atalho
$Pagina = Join-Path $Kit "painel\index.html"
$AtalhoPainel = Join-Path ([Environment]::GetFolderPath("Desktop")) "Painel do kit.url"
$url = ([System.Uri]$Pagina).AbsoluteUri
[System.IO.File]::WriteAllText($AtalhoPainel, ("[InternetShortcut]`r`nURL=" + $url + "`r`n"), (New-Object System.Text.ASCIIEncoding))
if (Test-Path $AtalhoPainel) {
  Ok "atalho criado na Area de Trabalho: Painel do kit"
  Painel etapa atalho ok "atalho do agente e Painel do kit na Area de Trabalho"
} else {
  Aviso "nao consegui criar o atalho do Painel do kit"
  Painel etapa atalho atencao "nao consegui criar o atalho do Painel do kit"
}

& $Py ferramentas\ambiente.py --conferir
if ($LASTEXITCODE -ne 0) { Parar 1 }
& $Py ferramentas\verificar.py
if ($LASTEXITCODE -ne 0) { Parar 1 }
# Os demais passos do onboarding podem ficar pendentes; a instalacao precisa estar pronta.
try {
  $Progresso = Get-Content (Join-Path $Kit ".root\progresso.json") -Raw -Encoding UTF8 | ConvertFrom-Json
  $Instalacao = @($Progresso.passos | Where-Object { $_.id -eq "instalar" -and $_.feito -eq $true })
  if ($Instalacao.Count -eq 0) { Aviso "a instalacao ainda tem pendencias; corrija a conferencia e rode de novo."; Parar 1 }
} catch {
  Aviso "nao consegui conferir o resultado da instalacao."
  Parar 1
}
Painel concluir
Write-Host ""
Write-Host "   O Painel do kit (no navegador e no atalho da Area de Trabalho) mostra o que ficou pronto," -ForegroundColor Cyan
Write-Host "   o que falta e os proximos passos com o texto para o agente do kit." -ForegroundColor Cyan
# o agente do kit pode abrir a conversa ja na pasta do kit (instalar\agente.ps1)
if (Get-Command Agente-Abrir -ErrorAction SilentlyContinue) { Agente-Abrir }
Fim 0
