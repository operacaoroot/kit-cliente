#!/bin/bash
# Parte do instalador que é do kit Codex. Carregada por instalar/instalar.sh (não rode direto).

agente_preparar() { :; }

agente_ligar() {
  if python3 -c "import json,sys;sys.exit(0 if json.load(open('.root/cliente.json')).get('mcp') else 1)" 2>/dev/null; then
    passo "Ligando o Codex ao servidor da empresa (MCP)"
    # Pede o token que a Root entregou (ou lê KIT_MCP_TOKEN), guarda em .root/mcp.env e registra no Codex.
    python3 ferramentas/mcp.py --registrar || falha "o servidor da empresa ficou sem registro; depois rode: python3 ferramentas/mcp.py --registrar"
  fi
}

agente_atalho() {
  passo "Criando o atalho do Codex do kit"
  ATALHO="$HOME/Desktop/Codex do kit.command"
  # O atalho carrega o token do servidor (.root/mcp.env) antes de abrir o Codex.
  printf '#!/bin/bash\nexport PATH="$HOME/.local/bin:$PATH"\ncd "%s" || exit 1\n[ -f .root/mcp.env ] && . .root/mcp.env\nexec codex\n' "$KIT" > "$ATALHO" && chmod +x "$ATALHO"
  if [ -x "$ATALHO" ]; then echo "atalho criado na Mesa: Codex do kit"; else falha "não consegui criar o atalho na Mesa; abra o Terminal na pasta do kit, rode '. .root/mcp.env' e depois codex"; fi
}
