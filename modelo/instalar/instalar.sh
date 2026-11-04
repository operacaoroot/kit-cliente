#!/bin/bash
# Instalador do kit (Mac e Linux). Prepara o computador a partir de ambiente/apps.json,
# cria o Python do kit, liga o kit ao GitHub (conta da pessoa ou chave do kit), faz o que o agente
# do kit pede (instalar/agente.sh: liberação, servidor da empresa, atalho) e roda a conferência.
# Pode rodar quantas vezes quiser: o que já está instalado é pulado.
# Opcionais do catálogo: bash instalar/instalar.sh --com vscode,docker
set -u
KIT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$KIT" || exit 1
SISTEMA="$(uname -s)"

passo() { printf '\n== %s\n' "$1"; }
falha() { printf '\n[atenção] %s\n' "$1"; }
# A parte que muda com o agente do kit (claude ou codex) mora em instalar/agente.sh:
# agente_preparar, agente_ligar e agente_atalho. O montador põe ali só a versão do agente deste kit.
. "$KIT/instalar/agente.sh"

passo "Conferindo as ferramentas básicas"
if [ "$SISTEMA" = "Darwin" ] && ! xcode-select -p >/dev/null 2>&1; then
  falha "O Mac precisa das ferramentas de linha de comando da Apple (elas trazem o git). Uma janela vai abrir: clique em Instalar, espere terminar e rode este instalador de novo."
  xcode-select --install
  exit 0
fi
command -v git >/dev/null 2>&1 || { falha "git não encontrado. No Linux: sudo apt install git"; exit 1; }
command -v python3 >/dev/null 2>&1 || { falha "python3 não encontrado. No Linux: sudo apt install python3"; exit 1; }
echo "git e Python do sistema ok"

python3 ferramentas/ambiente.py --instalar "$@"
export PATH="$HOME/.local/bin:$PATH"
python3 ferramentas/ambiente.py --venv

agente_preparar

passo "Ligando o kit ao GitHub"
# Com usuário do GitHub no kit: entra com a conta da pessoa (colaborador). Sem conta, ou se o
# login não terminar: liga pela chave do kit, que é só deste repositório.
if python3 -c "import json,sys;sys.exit(0 if json.load(open('.root/cliente.json')).get('github') else 1)" 2>/dev/null; then
  python3 ferramentas/conectar.py --conectar || { falha "seguindo pela chave do kit; dá para entrar no GitHub depois com: python3 ferramentas/conectar.py --conectar"; python3 ferramentas/conectar.py --usar-chave; }
else
  python3 ferramentas/conectar.py --usar-chave
fi

agente_ligar

if [ "$SISTEMA" = "Darwin" ]; then
  mkdir -p "$HOME/Desktop"
  agente_atalho
fi

passo "Conferência"
python3 ferramentas/ambiente.py --conferir
python3 ferramentas/verificar.py
