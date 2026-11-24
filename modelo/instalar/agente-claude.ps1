# Parte do instalador que e do kit Claude. Carregada por instalar\instalar.ps1 (nao rode direto).

function Agente-Preparar {
  # o computador, o Claude e o servidor sao da pessoa: o Claude trabalha sem pedir permissao
  & $Py ferramentas\autonomia.py
}

function Agente-Ligar { }

# Com o aplicativo do Claude instalado (protocolo claude:// registrado), o atalho abre a aba Code
# na pasta do kit com a primeira mensagem escrita: dali em diante o Claude conduz pela conversa.
# Sem o aplicativo, o atalho abre o Claude Code no terminal, como antes.
$MensagemInicial = "Oi%2C%20acabei%20de%20instalar%20o%20kit.%20Vamos%20come%C3%A7ar%3F"
function Agente-LinkDoApp {
  if (-not (Test-Path "Registry::HKEY_CLASSES_ROOT\claude")) { return $null }
  return ("claude://code/new?folder=" + [uri]::EscapeDataString($Kit) + "&q=" + $MensagemInicial)
}

function Agente-Atalho {
  $Mesa = [Environment]::GetFolderPath("Desktop")
  $Link = Agente-LinkDoApp
  if ($Link) {
    $Atalho = Join-Path $Mesa "Claude do kit.url"
    $linhas = @("[InternetShortcut]", ("URL=" + $Link))
    foreach ($exe in @((Join-Path $env:LOCALAPPDATA "AnthropicClaude\claude.exe"), (Join-Path $env:LOCALAPPDATA "Programs\Claude\Claude.exe"))) {
      if (Test-Path $exe) { $linhas += @(("IconFile=" + $exe), "IconIndex=0"); break }
    }
    [System.IO.File]::WriteAllText($Atalho, (($linhas -join "`r`n") + "`r`n"), (New-Object System.Text.ASCIIEncoding))
    $Antigo = Join-Path $Mesa "Claude do kit.cmd"
    if (Test-Path $Antigo) { Remove-Item $Antigo -Force }
  } else {
    $Atalho = Join-Path $Mesa "Claude do kit.cmd"
    $linhas = @("@echo off", ("cd /d """ + $Kit + """"), "set PATH=%USERPROFILE%\.local\bin;%PATH%", "claude")
    [System.IO.File]::WriteAllText($Atalho, (($linhas -join "`r`n") + "`r`n"), (New-Object System.Text.ASCIIEncoding))
  }
  if (Test-Path $Atalho) { Ok "atalho criado na Area de Trabalho: Claude do kit" } else { Aviso "nao consegui criar o atalho; abra a pasta do kit e rode claude" }
}

function Agente-Abrir {
  $Link = Agente-LinkDoApp
  if ($Link) {
    Ok "abrindo o Claude na pasta do kit: entre com a sua conta, confie na pasta e envie a mensagem"
    Start-Process $Link
  }
}
