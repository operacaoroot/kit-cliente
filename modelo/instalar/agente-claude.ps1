# Parte do instalador que e do kit Claude. Carregada por instalar\instalar.ps1 (nao rode direto).

function Agente-Preparar {
  # o computador, o Claude e o servidor sao da pessoa: o Claude trabalha sem pedir permissao
  & $Py ferramentas\autonomia.py
}

function Agente-Ligar { }

function Agente-Atalho {
  $Atalho = Join-Path ([Environment]::GetFolderPath("Desktop")) "Claude do kit.cmd"
  $linhas = @("@echo off", ("cd /d """ + $Kit + """"), "set PATH=%USERPROFILE%\.local\bin;%PATH%", "claude")
  [System.IO.File]::WriteAllText($Atalho, (($linhas -join "`r`n") + "`r`n"), (New-Object System.Text.ASCIIEncoding))
  if (Test-Path $Atalho) { Ok "atalho criado na Area de Trabalho: Claude do kit" } else { Aviso "nao consegui criar o atalho; abra a pasta do kit e rode claude" }
}
