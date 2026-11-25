# Parte do instalador que e do kit Codex. Carregada por instalar\instalar.ps1 (nao rode direto).

function Agente-Preparar { }

function Agente-Ligar {
  if ($Cliente.mcp) {
    Passo "Ligando o Codex ao servidor da empresa (MCP)"
    # Pede o token que a Root entregou (ou le KIT_MCP_TOKEN), guarda em .root\mcp.env e registra no Codex.
    & $Py ferramentas\mcp.py --registrar
    if ($LASTEXITCODE -ne 0) { Aviso "o servidor da empresa ficou sem registro; depois rode: .venv\Scripts\python ferramentas\mcp.py --registrar" }
  }
}

function Agente-Atalho {
  $Atalho = Join-Path ([Environment]::GetFolderPath("Desktop")) "Codex do kit.cmd"
  # O atalho carrega o token do servidor (.root\mcp.env, linhas VARIAVEL=valor) antes de abrir o Codex.
  $linhas = @("@echo off", ("cd /d """ + $Kit + """"), "set PATH=%USERPROFILE%\.local\bin;%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%", "if exist .root\mcp.env for /f ""usebackq tokens=1,* delims=="" %%a in ("".root\mcp.env"") do set ""%%a=%%b""", "codex")
  [System.IO.File]::WriteAllText($Atalho, (($linhas -join "`r`n") + "`r`n"), (New-Object System.Text.ASCIIEncoding))
  if (Test-Path $Atalho) { Ok "atalho criado na Area de Trabalho: Codex do kit" } else { Aviso "nao consegui criar o atalho; abra a pasta do kit e rode codex" }
}
