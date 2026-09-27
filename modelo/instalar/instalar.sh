#!/bin/bash
# Instalador do kit (Mac e Linux). Instala o que faltar, liga a chave do kit ao git
# e roda a conferência. Pode rodar quantas vezes quiser: o que já está instalado é pulado.
set -u
KIT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$KIT" || exit 1
SISTEMA="$(uname -s)"

passo() { printf '\n== %s\n' "$1"; }
falha() { printf '\n[atenção] %s\n' "$1"; }

passo "Conferindo o git e o Python"
if [ "$SISTEMA" = "Darwin" ] && ! xcode-select -p >/dev/null 2>&1; then
  falha "O Mac precisa das ferramentas de linha de comando da Apple. Uma janela vai abrir: clique em Instalar, espere terminar e rode este instalador de novo."
  xcode-select --install
  exit 0
fi
command -v git >/dev/null 2>&1 || { falha "git não encontrado. No Linux: sudo apt install git"; exit 1; }
command -v python3 >/dev/null 2>&1 || { falha "python3 não encontrado. No Linux: sudo apt install python3"; exit 1; }
echo "git e Python ok"

passo "Conferindo o Claude Code"
if ! command -v claude >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/claude" ]; then
  echo "Instalando o Claude Code pelo instalador oficial..."
  curl -fsSL https://claude.ai/install.sh | bash
fi
export PATH="$HOME/.local/bin:$PATH"
command -v claude >/dev/null 2>&1 && echo "Claude Code ok" || falha "O Claude Code não ficou disponível. Feche e abra o Terminal e rode de novo."

passo "Conferindo o Obsidian"
if [ "$SISTEMA" = "Darwin" ]; then
  if [ ! -d /Applications/Obsidian.app ] && [ ! -d "$HOME/Applications/Obsidian.app" ]; then
    if command -v brew >/dev/null 2>&1; then
      brew install --cask obsidian
    else
      falha "Baixe o Obsidian na página que vai abrir, arraste para Aplicativos e rode este instalador de novo."
      open "https://obsidian.md/download"
    fi
  else
    echo "Obsidian ok"
  fi
else
  command -v obsidian >/dev/null 2>&1 || falha "Instale o Obsidian em https://obsidian.md/download"
fi

passo "Ligando a chave do kit"
if [ -f "$KIT/.root/chave" ]; then
  chmod 600 "$KIT/.root/chave"
  git config core.sshCommand "ssh -i \"$KIT/.root/chave\" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
  NOME="$(python3 -c "import json;print(json.load(open('.root/cliente.json'))['nome'])" 2>/dev/null)"
  SLUG="$(python3 -c "import json;print(json.load(open('.root/cliente.json'))['slug'])" 2>/dev/null)"
  [ -n "$NOME" ] && git config user.name "$NOME"
  [ -n "$SLUG" ] && git config user.email "kit-$SLUG@kit.operacaoroot.com"
  echo "chave ligada"
else
  falha "A chave do kit (.root/chave) não veio junto. Fale com a Root."
fi

passo "Criando o atalho do Claude do kit"
if [ "$SISTEMA" = "Darwin" ]; then
  ATALHO="$HOME/Desktop/Claude do kit.command"
  printf '#!/bin/bash\ncd "%s" && exec claude\n' "$KIT" > "$ATALHO"
  chmod +x "$ATALHO"
  echo "atalho criado na Mesa: Claude do kit"
fi

passo "Conferência"
python3 ferramentas/verificar.py
