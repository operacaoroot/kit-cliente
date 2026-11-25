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
#    4) o resto do catalogo ambiente\apps.json pelo perfil do kit (Claude Code, Obsidian...)
#       e libera o Claude para trabalhar sem pedir permissao (ferramentas\autonomia.py)
#    5) liga o kit a Root pela chave que veio no kit (sem conta nem codigo do GitHub)
#    6) cria os atalhos e roda a conferencia; o painel mostra o que falta e os proximos passos
# ============================================================================
param([string]$Com = "")
$ErrorActionPreference = "Continue"
$Kit = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Kit
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
if (-not (Test-Path $Py)) { uv venv --python 3.12 (Join-Path $Kit ".venv") }
if (Test-Path $Py) {
  uv pip install --quiet --python $Py -r (Join-Path $Kit "ambiente\requirements.txt")
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
  else { Aviso "o Git nao ficou disponivel. Feche esta janela, abra de novo e rode outra vez."; Painel etapa basico falhou "o Git nao ficou disponivel; rode o instalador de novo" }
}
else {
  Aviso "este Windows nao tem o winget. Instale o 'Instalador de Aplicativo' pela Microsoft Store e rode de novo."
  Painel etapa basico falhou "falta o Instalador de Aplicativo (winget) da Microsoft Store"
  Painel concluir
  Start-Process "https://apps.microsoft.com/detail/9NBLGGH4NNS1"
  Fim 1
}

# ---------- 4) o resto do catalogo ----------
Passo "4/6 Claude Code, Obsidian e o que o seu perfil pede"
Painel etapa programas andamento "instalando o que falta; o Windows pode pedir permissao, clique em Sim"
$argsAmbiente = @("ferramentas\ambiente.py", "--instalar")
if ($Com) { $argsAmbiente += @("--com", $Com) }
& $Py @argsAmbiente
if ($LASTEXITCODE -eq 0) { Painel etapa programas ok "programas do kit instalados" }
else { Painel etapa programas atencao "algum programa nao ficou instalado; veja a lista do que falta" }
Recarregar-Path

# o computador, o Claude e o servidor sao da pessoa: o Claude trabalha sem pedir permissao
Painel etapa autonomia andamento
& $Py ferramentas\autonomia.py
if ($LASTEXITCODE -eq 0) { Painel etapa autonomia ok "o Claude trabalha sem pedir permissao a cada passo" }
else { Painel etapa autonomia atencao "nao consegui gravar a liberacao do Claude" }

# ---------- 5) chave do kit ----------
Passo "5/6 Ligando o kit a Root"
# Sempre pela chave que veio no kit: sem conta, sem login e sem codigo do GitHub.
Painel etapa chave andamento "pela chave que veio no kit"
& $Py ferramentas\conectar.py --usar-chave
if ($LASTEXITCODE -eq 0) { Painel etapa chave ok "kit ligado pela chave; sem conta nem codigo do GitHub" }
else { Painel etapa chave falhou "a chave do kit nao veio no ZIP; extraia o ZIP inteiro de novo" }

# ---------- 6) atalhos e conferencia ----------
Passo "6/6 Atalhos e conferencia"
Painel etapa atalho andamento
$Mesa = [Environment]::GetFolderPath("Desktop")
$Atalho = Join-Path $Mesa "Claude do kit.cmd"
$linhas = @("@echo off", ("cd /d """ + $Kit + """"), "set PATH=%USERPROFILE%\.local\bin;%PATH%", "claude")
[System.IO.File]::WriteAllText($Atalho, (($linhas -join "`r`n") + "`r`n"), (New-Object System.Text.ASCIIEncoding))
$Pagina = Join-Path $Kit "painel\index.html"
$AtalhoPainel = Join-Path $Mesa "Painel do kit.url"
$url = ([System.Uri]$Pagina).AbsoluteUri
[System.IO.File]::WriteAllText($AtalhoPainel, ("[InternetShortcut]`r`nURL=" + $url + "`r`n"), (New-Object System.Text.ASCIIEncoding))
if ((Test-Path $Atalho) -and (Test-Path $AtalhoPainel)) {
  Ok "atalhos criados na Area de Trabalho: Claude do kit e Painel do kit"
  Painel etapa atalho ok "Claude do kit e Painel do kit na Area de Trabalho"
} else {
  Aviso "nao consegui criar os atalhos; abra a pasta do kit e rode claude"
  Painel etapa atalho atencao "nao consegui criar os atalhos na Area de Trabalho"
}

& $Py ferramentas\ambiente.py --conferir
& $Py ferramentas\verificar.py
Painel concluir
Write-Host ""
Write-Host "   O Painel do kit (no navegador e no atalho da Area de Trabalho) mostra o que ficou pronto," -ForegroundColor Cyan
Write-Host "   o que falta e os proximos passos com o texto para o Claude." -ForegroundColor Cyan
Fim 0
