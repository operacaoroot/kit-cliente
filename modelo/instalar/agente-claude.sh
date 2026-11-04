#!/bin/bash
# Parte do instalador que é do kit Claude. Carregada por instalar/instalar.sh (não rode direto).

agente_preparar() {
  passo "Liberando o Claude para trabalhar sem pedir permissão"
  python3 ferramentas/autonomia.py
}

agente_ligar() { :; }

agente_atalho() {
  passo "Criando o atalho do Claude do kit"
  ATALHO="$HOME/Desktop/Claude do kit.command"
  printf '#!/bin/bash\nexport PATH="$HOME/.local/bin:$PATH"\ncd "%s" && exec claude\n' "$KIT" > "$ATALHO" && chmod +x "$ATALHO"
  if [ -x "$ATALHO" ]; then echo "atalho criado na Mesa: Claude do kit"; else falha "não consegui criar o atalho na Mesa; abra o Terminal na pasta do kit e digite claude"; fi
}
